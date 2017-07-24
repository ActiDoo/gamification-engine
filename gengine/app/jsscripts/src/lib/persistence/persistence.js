import merge from 'lodash/merge';
import cloneDeep from 'lodash/cloneDeep';

export const ENABLE_PERSISTENCE_MIDDLEWARE = "ENABLE_PERSISTENCE_MIDDLEWARE"
export const LOAD_REDUX_STORE_FROM_LOCAL_STORAGE = "LOAD_REDUX_STORE_FROM_LOCAL_STORAGE";
export const LOAD_REDUX_STORE_FROM_LOCAL_STORAGE_CANCEL = "LOAD_REDUX_STORE_FROM_LOCAL_STORAGE_CANCEL";

/**

 How does it work?

 - A middleware is created which extracts all to be persisted store values and copies them to the localStorage
 - A reducer loads all persisted elements from the localStorage into the store
 - The loading action is triggered after the initial rendering in index.js. During the rendering, some components
 already invoke other actions, whose results may not be persisted (that would overwrite the stored state).
 Thus, we need to enable the middleware after the initial loading using another action.

 **/

/**
 Middleware to copy the persistent store values to the sessionStorage
 The keys must be list of paths in the store, e.g.:
 [
    ["data","units"],
 ....
 ]
 **/

export const getLocalPersistenceMiddleware = persistenceKeys => store => next => action => {
    const nextResult = next(action);
    if(localStorage && action.type != ENABLE_PERSISTENCE_MIDDLEWARE) {
        const newState = store.getState();
        if (newState.localPersistence && newState.localPersistence.middlewareEnabled == true) {
            const persistentState = {};

            for(const path of persistenceKeys) {
                let source = newState;
                for(const pathItem of path) {
                    source = source[pathItem];
                }
                let target = persistentState;
                for(let i=0; i<path.length; i++){
                    const pathItem = path[i];
                    if(i==path.length-1) {
                        target[pathItem] = source;
                    } else {
                        if(!(pathItem in target)) {
                            target[pathItem] = {};
                        }
                        target = target[pathItem];
                    }
                }
            }
            localStorage.reduxStorePersistence = JSON.stringify(persistentState);
        }
    }

    return nextResult;
}

/* Reducer */

const init_state = {
    middlewareEnabled : false,
    inizialized : false,
};

const is_initialized = {
    localPersistence: {
        inizialized: true
    }
}

export const localPersistenceReducer = (state=init_state, action="") => {

    if(action.type == LOAD_REDUX_STORE_FROM_LOCAL_STORAGE) {

        if(action.payload.localStorageState && action.payload.localStorageState!='' && action.payload.persistenceKeys){

            // Delete existing values that will be restored first....
            const tmpState = cloneDeep(state);
            for(let keylist of action.payload.persistenceKeys) {
                let target = tmpState;
                for(let i=0; i<keylist.length; i++) {
                    let key = keylist[i];
                    if(i==keylist.length-1 && typeof target[key] != 'undefined') {
                        //last item, delete
                        delete target[key];
                    } else if(typeof target[key] != 'undefined') {
                        //traverse
                        target = target[key]
                    } else {
                        //path is not set, break
                        break;
                    }
                }
            }
            let newState = merge(merge(state,action.payload.localStorageState), is_initialized);
            return cloneDeep(newState);

        }else{
            return merge(state, is_initialized);
        }
    } else if (action.type == LOAD_REDUX_STORE_FROM_LOCAL_STORAGE_CANCEL){

        return {
            ...state,
            inizialized : true
        }

    } else if (action.type == ENABLE_PERSISTENCE_MIDDLEWARE) {
        return {
            ...state,
            middlewareEnabled : true
        }
    }
    return state;
}

/* Action Creators */

export const enableLocalStoragePersistenceMiddleware = () => {
    return {
        type : ENABLE_PERSISTENCE_MIDDLEWARE
    }
}

const parseDataFromLocalStorage = () => {

    let output = null;

    try {
        output = JSON.parse(localStorage.reduxStorePersistence, (key, value) => {
            if (typeof value === 'string') {
                let isDate = /(\d{4})-(\d{2})-(\d{2})T((\d{2}):(\d{2}):(\d{2}))\.(\d{3})Z/.test(value);
                if (isDate) {
                    return new Date(value);
                }
            }
            return value;
        });
    }
    catch(err) {
        console.error(err);
        console.error("error while parsing LocalStorage State: ", localStorage.getItem(this.localPersistencePathKey));
    }

    return output;
}

export const loadReduxStoreFromLocalStorage = () => {
    if(localStorage && ("reduxStorePersistence" in localStorage)) {
        return {
            type : LOAD_REDUX_STORE_FROM_LOCAL_STORAGE,
            payload : {
                localStorageState : parseDataFromLocalStorage()
            }
        }
    }else{
        return {
            type : LOAD_REDUX_STORE_FROM_LOCAL_STORAGE_CANCEL,
        }
    }
    return null;
}
