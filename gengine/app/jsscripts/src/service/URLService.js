import { browserHistory } from 'react-router';
import URI from 'urijs';
import _ from 'lodash';

export default class URLService {

    static getCurrentPathWithSearch() {
        let currentPath = window.location.pathname;
        let currentSearch = window.location.search;
        return currentPath + currentSearch;
    }

    static setQueryParameter(name, value) {
        browserHistory.replace(URI(this.getCurrentPathWithSearch()).setQuery(name,value).toString());
    }

    static addQueryParameter(name, value) {
        browserHistory.replace(URI(this.getCurrentPathWithSearch()).addQuery(name,value).toString());
    }

    static removeQueryParameterWithValue(name, value) {
        browserHistory.replace(URI(this.getCurrentPathWithSearch()).removeQuery(name,value).toString());
    }

    static removeQueryParameter(name) {
        browserHistory.replace(URI(this.getCurrentPathWithSearch()).removeQuery(name).toString());
    }

    static toggleQueryParameter(name, value) {
        let uri = URI(this.getCurrentPathWithSearch());
        if(uri.hasQuery(name, value, true)) {
            this.removeQueryParameterWithValue(name, value)
        } else {
            this.addQueryParameter(name, value)
        }
    }

    static getQueryParameterValueAsList(name) {
        let qry = URI(this.getCurrentPathWithSearch()).query(true);

        if(!qry[name]) return [];
        if(!_.isArray(qry[name])) {
            return [qry[name]]
        }
        return qry[name]
    }

    static getQueryParameterValueAsIntList(name) {
        let qry = URI(this.getCurrentPathWithSearch()).query(true);

        if(!qry[name]) return [];
        if(!_.isArray(qry[name])) {
          return [parseInt(qry[name])]
        }
        let list = qry[name];
        return _.map(list, (it) => {
            return parseInt(it);
        })
    }

    static getQueryParameterAsBool(name) {
        let qry = URI(this.getCurrentPathWithSearch()).query(true);

        if(!qry[name]) {
            return false;
        } else {
            return true;
        }
    }

    static getQueryParameterAsInt(name) {
        let qry = URI(this.getCurrentPathWithSearch()).query(true);

        if(typeof qry[name] == 'undefined') {
            return null;
        } else {
            return parseInt(qry[name]);
        }
    }

    static getQueryParameterAsString(name, fallback=null) {
        let qry = URI(this.getCurrentPathWithSearch()).query(true);

        if(typeof qry[name] == 'undefined') {
            return fallback;
        } else {
            return ""+qry[name];
        }
    }
}