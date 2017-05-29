import {
    getLocalPersistenceMiddleware,
    enableLocalStoragePersistenceMiddleware,
    localPersistenceReducer,
    loadReduxStoreFromLocalStorage,
    LOAD_REDUX_STORE_FROM_LOCAL_STORAGE
} from './persistence';

export {
    // The Middleware to save all store changes to the persistence store
    getLocalPersistenceMiddleware,
    // The reducer loads all persisted element into the store
    // And enables the middleware
    localPersistenceReducer,
    // Action Creator to enable the Middleware
    enableLocalStoragePersistenceMiddleware,
    /*
     const store = createStore(rootReducer, composeWithDevTools(
        applyMiddleware(sagaMiddleware, getLocalPersistenceMiddleware([
            // Store paths, that should be persisted
            // e.g. [["auth","user"],["auth","token"]]
            //...data.localPersistence.map(x => ["data",...x]),
        ])),
     ));
    */
    // The action creator to trigger the loading
    loadReduxStoreFromLocalStorage,
    // The action type for loading is needed to create the RootReducer, as it has to work on the full state
    /*

     const rootReducer = (state,action) => {
        if(action.type == LOAD_REDUX_STORE_FROM_LOCAL_STORAGE) {
            return localPersistenceReducer(state, action);
        } else {
            return combinedReducer(state, action);
        }
     }

     */
    LOAD_REDUX_STORE_FROM_LOCAL_STORAGE
}