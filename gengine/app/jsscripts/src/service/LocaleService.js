import messages from '../locales';

export const getUserLocale = () => {

  let userLocale = 'en';
  var language = navigator.languages && navigator.languages[0] ||
                 navigator.language ||
                 navigator.userLanguage;
  if(messages[language] != null){
    userLocale = language;
  }else if(messages[language.split('-')[0]] != null){
    userLocale = language.split('-')[0];
  }

  return userLocale;
}

export const getInitialLocale = () => {

  //check window locale
  if(window && window.location && window.location.pathname){
    const urlParts = window.location.pathname.split('/');
    if(urlParts.length > 1){
      if(messages[urlParts[1]]){
        return urlParts[1];
      }
    }
  }

  return getUserLocale();

}
