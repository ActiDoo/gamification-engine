import * as types from './constants';

export function setLocale(locale, initial) {
  return { type: types.SET_LOCALE, payload: { locale: locale } };
}
