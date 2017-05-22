'use strict';

let _export = {};

_export.colors = {
  "primary1" : "#f1f1f1",
  "primary2": "#989b9d",
  "secondary1": "#FFFFFF",
  "secondary2": "#FFFFFF",
  "white" : "#FFFFFF",
  "black" : "#000000",
}
// Let's make all colors available in the root (i.e. $primary1)
for( let key in _export.colors) {
  _export[key] = _export.colors[key];
}

_export.layout = {
  "mobile-max" : "(max-width : 980px)",
  "mobile-min" : "(min-width : 981px)"
}
// Let's make all layout settings available in the root (i.e. $mobile-max)
for( let key in _export.layout) {
  _export[key] = _export.layout[key];
}

_export.fontsizes = {
  "fontsize-small" : "10px",
  "fontsize-normal" : "12px",
  "fontsize-big" : "14px",
}
// Let's make all fontsizes available in the root (i.e. $primary1)
for( let key in _export.fontsizes) {
  _export[key] = _export.fontsizes[key];
}


module.exports = _export;
