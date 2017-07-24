
import MobileDetect from 'mobile-detect';
const md = new MobileDetect(window.navigator.userAgent);
const mobile = md.mobile();
const os = md.os();

export const getDimensions = () => {

  let width = window.innerWidth
  || document.documentElement.clientWidth
  || document.body.clientWidth;

  let height = window.innerHeight
  || document.documentElement.clientHeight
  || document.body.clientHeight;

  return {width, height};
};

export const isMobile = () => {
    return mobile
};

export const isAndroid = () => {
    return os=='AndroidOS';
};

export const isIos = () => {
  return os=='iOS';
};

export const isIpad = () => {
  return md.is('iPad');
};

export const isBlackBerry = () => {
  return os=="BlackBerryOS";
}

export const isFF = () => {
  return navigator.userAgent.toLowerCase().indexOf('firefox') > -1;
}

export const isIE = () => {
  var ua = window.navigator.userAgent;

  var msie = ua.indexOf('MSIE ');
  if (msie > 0) {
      // IE 10 or older => return version number
      return parseInt(ua.substring(msie + 5, ua.indexOf('.', msie)), 10);
  }

  var trident = ua.indexOf('Trident/');
  if (trident > 0) {
      // IE 11 => return version number
      var rv = ua.indexOf('rv:');
      return parseInt(ua.substring(rv + 3, ua.indexOf('.', rv)), 10);
  }

  var edge = ua.indexOf('Edge/');
  if (edge > 0) {
     // Edge (IE 12+) => return version number
     return parseInt(ua.substring(edge + 5, ua.indexOf('.', edge)), 10);
  }

  // other browser
  return false;
}
