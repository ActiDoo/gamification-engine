import { createSelector } from 'reselect'

export const getState = (state) => state.ui;

export const getLocale = createSelector(
    getState,
    (ui) => ui.locale
);
