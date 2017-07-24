import * as types from "./constants";
import {getInitialLocale} from '../../service/LocaleService';

let initState = {
  locale: getInitialLocale(),
};

export default function reducer(state = initState, action = "") {

  if(action.type.startsWith(types.PREFIX)){

    switch (action.type) {
      case types.SET_LOCALE:
        return {
          ...state,
          locale: action.payload.locale,
        }
        break;
      default:
        return state
        break;
    }
  }

  return state;
}
