import {IntlProvider, defineMessages, addLocaleData} from 'react-intl';

import en from 'react-intl/locale-data/en';
import de from 'react-intl/locale-data/de';

addLocaleData([
  ...en,
  ...de,
]);
