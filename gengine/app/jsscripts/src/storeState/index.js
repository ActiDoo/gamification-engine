import _ from 'lodash';
import { combineReducers } from "redux";
import { fork } from 'redux-saga/effects';
import { createStore, applyMiddleware } from 'redux';
import createSagaMiddleware from 'redux-saga'
import { composeWithDevTools } from 'remote-redux-devtools';

import {getLocalPersistenceMiddleware, localPersistenceReducer, LOAD_REDUX_STORE_FROM_LOCAL_STORAGE} from '../lib/persistence';
import {buildSwaggerApi} from '../lib/swagger';
import apiConfig from './apiConfig';
import ui from './ui';

//import data from "./data";

export default function initStore() {
    return buildSwaggerApi(apiConfig).then(function(api) {
        console.log(api)
        const sagaMiddleware = createSagaMiddleware();

        const combinedReducer = combineReducers({
            api: api.reducer,
            ui: ui.reducer,
            localPersistence : localPersistenceReducer
            //data: data.reducer,
        });

        const rootReducer = (state,action) => {
            if(action.type == LOAD_REDUX_STORE_FROM_LOCAL_STORAGE) {
                return localPersistenceReducer(state, action);
            } else {
                return combinedReducer(state, action);
            }
        }

        const store = createStore(rootReducer, composeWithDevTools(
            applyMiddleware(sagaMiddleware, getLocalPersistenceMiddleware([
                //...data.localPersistence.map(x => ["data",...x]),
                ...api.persist.map(x => ["api",...x]),
                ...ui.persist.map(x => ["ui",...x])
            ])),
        ));

        var n_errors = 0
        const max_errors = 100;

        function* rootSaga () {
            try {
                yield [
                    fork(api.saga),
                ];
            } catch (e) {
                n_errors++;
                console.log("Error While executing Saga", e);
                if(n_errors < max_errors) {
                    yield [
                        fork(rootSaga)
                    ]
                }
            }
        }

        sagaMiddleware.run(rootSaga);

        return {
            store,
            dynamic: {
                api
            }
        };
    })
}
