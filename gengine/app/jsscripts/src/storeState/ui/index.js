import reducer from './reducer';
import * as actions from './actions';
import * as constants from './constants';
import * as selectors from './selectors';
import persist from './persist';

export default {
  reducer: reducer,
  actions: actions,
  constants: constants,
  selectors: selectors,
  persist: persist
};
