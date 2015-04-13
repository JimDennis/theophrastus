function parseQuery (query) {
   var Params = new Object ();
   if (!query) return Params; // return empty object
   var Pairs = query.split(/[;&]/);
   for (var i = 0; i < Pairs.length; i++) {
      var KeyVal = Pairs[i].split('=');
      if (!KeyVal || KeyVal.length != 2) continue;
      var key = unescape(KeyVal[0]);
      var val = unescape(KeyVal[1]);
      val = val.replace(/\+/g, ' ');
      Params[key] = val;
   }
   return Params;
}

var scripts = document.getElementsByTagName('script');
var myScript = scripts[ scripts.length - 1 ];
var queryString = myScript.src.replace(/^[^\?]+\??/,'');
var params = parseQuery( queryString );

document.cookie = "alert=;expires=Thu, 01-Jan-1970 00:00:01 GMT"
alert(params['arg']);
