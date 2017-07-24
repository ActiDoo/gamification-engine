import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';
import GroupAssignment from './components/views/group-assignment/GroupAssignment';
import LeaderboardCreation from './components/views/leaderboard-creation/LeaderboardCreation';

import { initStoreState } from './storeState';
import { enableLocalStoragePersistenceMiddleware, loadReduxStoreFromLocalStorage } from './lib/persistence';
import initStore from './storeState';

import 'react-select/dist/react-select.css';
import 'input-moment/dist/input-moment.css';

const init = (component, domElement) => {

    const renderApp = () => {
        initStore().then(({store, dynamic}) => {
            ReactDOM.render(
                <App store={store} dynamic={dynamic}>{component}</App>,
                domElement
            );
            store.dispatch(enableLocalStoragePersistenceMiddleware());
            let loadAction = loadReduxStoreFromLocalStorage();
            if(loadAction) {
                store.dispatch(loadAction);
            }
            console.log("dynamic", dynamic);
        }).catch(function(e) {
            console.error(e);
        });
    }

    function runMyApp() {
        renderApp();
    }

    if (!global.Intl) {
        require.ensure([
            'intl',
            'intl/locale-data/jsonp/en.js',
            'intl/locale-data/jsonp/de.js'
        ], function (require) {
            require('intl');
            require('intl/locale-data/jsonp/en.js');
            require('intl/locale-data/jsonp/de.js');
            runMyApp()
        });
    } else {
        runMyApp()
    }
}

window.gengine = {
  'renderComponent': (domElement, component) => {
    if(component=="GroupAssignment") {
      init(<GroupAssignment />,domElement);
    }
    if(component=="LeaderboardCreation") {
      init(<LeaderboardCreation />,domElement);
    }
  }
};
