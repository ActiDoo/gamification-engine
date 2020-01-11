import Swagger from 'swagger-client';
import _ from 'lodash';
import { takeEvery, takeLatest } from 'redux-saga';
import { fork, call, put, apply } from 'redux-saga/effects';
import uuidV4 from 'uuid/v4';


function constify(text) {
    return text.toString().toUpperCase()
        .replace(/\s+/g, '_')        // Replace spaces with _
        .replace(/[^\w_]+/g, '')     // Remove all non-word chars
        .replace(/__+/g, '_')        // Replace multiple _ with single _
        .replace(/^_+/, '')          // Trim _ from start of text
        .replace(/_+$/, '');         // Trim _ from end of text
}

function camelifyString(str) {
    return constify(str).toLowerCase().replace(/[-_]([a-z])/g, function (g) { return g[1].toUpperCase(); })
}

export function generateID() {
    return uuidV4();
}

export function buildSwaggerApi(config) {
    /*

    config = {
        id: "appapi", // unique global identifier (used for store)
        url: "http://127.0.0.1:6543/api/_swagger",
        apis: {
            default: {
                echo_test: {
                    responseReducer = ({state, data, is_error}) => {
                        ...state,
                        echo_data:
                    }
                }
            }
        }
    }

    */

    config = Object.assign({},{
        id: "appapi", // unique global identifier (used for store)
        url: window.ADMIN_API_BASE_URL + "/api/_swagger",
        dummyError: {
            status: "unknown",
            message: "An unknown error has occurred.",
        }
    }, config);

    return new Swagger({
        url: config.url,
        usePromise: true
    })
    .then(function(client) {

        const types = [];
        const actions = {};
        const sagas = {};
        const reducers = [];
        const selectors = {};

        const PREFIX = constify(config.id);
        //console.log("spec",client.spec);
        //console.log("apis",client.apis);

        // The operations (executable functions) are nested inside the tags in client.apis
        // Since the operationIds are globally unique, we can flatten this
        const operations = {};
        for(let tag in client.apis) {
            for(let op in client.apis[tag]) {
                operations[op] = client.apis[tag][op];
            }
        }
        //same for specs
        const specs = {};
        for(let path in client.spec.paths) {
          for(let method in client.spec.paths[path]) {
            specs[client.spec.paths[path][method].operationId] = client.spec.paths[path][method];
            specs[client.spec.paths[path][method].operationId]["method"] = method;
         }
        }

        //for(let i=0; i<client.apisArray.length; i++) {
        //    let api = client.apisArray[i];
        //    for(let j=0; j<api.operationsArray.length; j++) {
        for(let op in operations) {
            let operation = operations[op];
            let operationName = constify(op);
            const camelifiedOperationName = camelifyString(operationName);

            let operationConfig = null;

            try {
                operationConfig = config.apis[camelifiedOperationName];
            } catch(e) {
                operationConfig = {};
            }

            // types
            let TYPE_REQ = types[PREFIX + operationName+'_REQUEST'] = PREFIX + operationName+'_REQUEST';
            let TYPE_RESP = types[PREFIX + operationName+'_RESPONSE'] = PREFIX + operationName+'_RESPONSE';

            // action creators
            let ACTION_REQ = actions[camelifyString(operationName+'_REQUEST')] = function(params) {
                if(!params) {
                  params = {};
                }
                if(!params.requestID) {
                  params.requestID = generateID();
                  //console.error(camelifyString(operationName+'_REQUEST')+" needs a requestID");
                }
                return { type: TYPE_REQ, payload: {params: params} };
            }
            let ACTION_RESP = actions[camelifyString(operationName+'_RESPONSE')] = function({ payload, error }) {
                return { type: TYPE_RESP, payload: payload, error: error };
            }

            // saga
            sagas[TYPE_REQ] = [];
            sagas[TYPE_REQ].push({
                type: specs[op].method.toLowerCase()=="get" ? 'latest' : 'every',
                func: function* (action) {
                    const run = (params) => {
                        return new Promise((resolve, reject) => {
                            // we have to split the params in body and non-body params
                            const body_params = {};
                            const non_body_params = {};
                            const body_spec = _.find(specs[op].parameters, (s) => s.in=="body");
                            for(let param in params) {
                                if(body_spec && body_spec.schema.properties[param]) {
                                    body_params[param] = params[param];
                                } else {
                                    non_body_params[param] = params[param];
                                }
                            };
                            //console.log("body_params", body_params);
                            //console.log("non_body_params", non_body_params);
                            let combined_params = non_body_params;
                            if(Object.keys(body_params).length>0) {
                                combined_params = {...combined_params, body: body_params};
                            }
                            operation(combined_params)
                            //client.execute({operationId: op, parameters: combined_params })
                                .then(function(response) {
                                    resolve(response);
                                })
                                .catch(function(response) {
                                    resolve(response);
                                })
                        });
                    }
                    const response = yield call(run, action.payload.params);
                    const error = response.status !== 200;
                    yield put(ACTION_RESP({ payload: {data: response.obj, requestParams: action.payload.params}, error: error }));
                }
            })

            // reducer

            let initState = {
                error: {},
                loading: {},
                data: {}
            };

            let responseReducer = null;
            if(operationConfig && operationConfig.responseReducer) {
                responseReducer = operationConfig.responseReducer
            } else {
                responseReducer = ({state, data, requestParams, is_error}) => {
                    let newState = {...state};
                    if(!newState[camelifiedOperationName]) {
                        newState[camelifiedOperationName] = {};
                    }
                    newState[camelifiedOperationName] = {
                        ...newState[camelifiedOperationName],
                    }
                    newState[camelifiedOperationName][requestParams.requestID] = is_error ? null : data;
                    newState[camelifiedOperationName]["latest"] = is_error ? null : data;
                    return newState;
                }
            }

            reducers.push(function(state=initState, action="") {
                if(action && action.type && action.type.startsWith(PREFIX)) {
                    let newState;
                    switch (action.type) {
                        case TYPE_REQ:
                            newState = {
                                ...state,
                            }
                            if(!newState.loading[camelifiedOperationName]) {
                                newState.loading[camelifiedOperationName] = [];
                            }
                            newState.loading[camelifiedOperationName] = [
                                ...newState.loading[camelifiedOperationName],
                                action.payload.params
                            ]
                            return newState
                        case TYPE_RESP:
                            let newData=state.data;
                            //debugger;
                            try {
                                newData = responseReducer({state: state.data, requestParams: action.payload.requestParams, data: action.payload.data, is_error: action.error})
                            } catch(e) {
                                console.error("Error executing responseReducer["+camelifiedOperationName+"]", e);
                              }
                              newState = {
                                ...state,
                                data: newData,
                              }
                              if(!newState.loading[camelifiedOperationName]) {
                                newState.loading[camelifiedOperationName] = [];
                              }
                              if(!newState.error[camelifiedOperationName]) {
                                newState.error[camelifiedOperationName] = [];
                            }
                            _.remove(newState.error[camelifiedOperationName], x => _.eq(x.requestID, action.payload.requestParams.requestID))
                            if(action.error) {
                                let errorData;
                                if(action.payload.data) {
                                  errorData = action.payload.data
                                } else {
                                  errorData = config.dummyError
                                }
                                newState.error[camelifiedOperationName].push({
                                  requestID: action.payload.requestParams.requestID,
                                  params: action.payload.requestParams,
                                  errorData: errorData
                                });
                            }
                            _.remove(newState.loading[camelifiedOperationName], x => _.eq(x, action.payload.requestParams.requestID))
                            return newState;
                        default:
                            return state;
                            break;
                    }
                }
                return state;
            })

            selectors[camelifyString("get_"+operationName+"_data")] = function(state) {
              //debugger;
              return state.data[camelifiedOperationName];
            }

            selectors[camelifyString("get_"+operationName+"_loading")] = function(state) {
                return state.loading[camelifiedOperationName];
            }

            selectors[camelifyString("get_"+operationName+"_error")] = function(state) {
                return state.error[camelifiedOperationName];
            }
        }

        const finalReducer = (state, action) => {
            for(let reducer of reducers) {
                state = reducer(state, action);
            }
            return state;
        }

        function* finalSaga() {
            let forks = [];
            for(let type in sagas) {
                for(let saga of sagas[type]) {
                    forks.push(fork(function*() {
                        if(saga.type=="every") {
                            yield* takeEvery(type, saga.func);
                        } else if(saga.type=="latest") {
                            yield* takeLatest(type, saga.func);
                        }
                    }))
                }
            }
            yield forks
        }

        return {
            types,
            actions,
            saga: finalSaga,
            reducer: finalReducer,
            persist: (config.persist || []).map(x => ["data",...x]),
            selectors: Object.assign([], selectors, config.selectors)
        }
    })
    .catch(function(error) {
        console.error('Oops! Can\'t connect to swagger. ' + error.statusText);

        const types = [];
        const actions = {};
        const saga = () => {};

        let initState = {
            error: {},
            loading: {},
            data: {}
        };
        const reducer = (state=initState, action) => {
            return state;
        };

        const persist = [];
        const selectors = [];

        return {
            types,
            actions,
            saga,
            reducer,
            persist,
            selectors
        }
    })
}
