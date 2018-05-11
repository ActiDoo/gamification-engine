
const method = {
  GET: 'GET',
  PUT: 'PUT',
  POST: 'POST',
  DELETE: 'DELETE',
  HEAD: 'HEAD',
}

export default class FetchService {

  static get(url) {
    return FetchService.fetch({
      url: url,
      method: method.GET
    });
  }

  static put(url, data) {
    return FetchService.fetch({
      url: url,
      method: method.PUT,
      body: JSON.stringify(data),
      headers: FetchService.getJsonHeaders(),
    });
  }

  static post(url, data) {

    return FetchService.fetch({
      url: url,
      method: method.POST,
      body: JSON.stringify(data),
      headers: FetchService.getJsonHeaders(),
    });
  }

  static delete(url, data) {
    return FetchService.fetch({
      url: url,
      method: method.DELETE,
      body: JSON.stringify(data),
      headers: FetchService.getJsonHeaders(),
    });
  }

  static head(url) {
    return FetchService.fetch({
      url: url,
      method: method.HEAD,
    });
  }

  static getJsonHeaders(){
    var headers = new Headers();
    headers.append('Accept', 'application/json');
    headers.append('Content-Type', 'application/json');
    return headers;
  }

  static fetch(params) {

    return new Promise((resolve, reject) => {
      fetch(params.url, params)
        .then(
          function (response) {

            var contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
              response.json().then((jsonResult) => {
                resolve({
                  response: response,
                  data: jsonResult
                });
              }).catch(error => {
                console.error("Parse error", error);
                reject(error);
              });
            } else {
              resolve({
                response: response
              });
            }
          }
        )
        .catch(function (error) {
          console.error("Fetch error", error);
          reject(error);
        });
    });
  }
}
