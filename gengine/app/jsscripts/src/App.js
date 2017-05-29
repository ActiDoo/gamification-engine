import React, { Component, PropTypes } from 'react';
import { Provider } from 'react-redux';
import { IntlProvider } from 'react-intl';
import { DynamicProvider } from './lib/swagger';
import { bindActionCreators } from "redux";
import { connect } from "react-redux";
import * as UIActions from './storeState/ui/actions';
import { getLocale } from './storeState/ui/selectors';
import messages from './locales';
import './App.css'

class App extends Component {

  componentWillMount = () => {
    let lang = this.props.lang;
    if(!messages[lang]){
      lang = "en";
    }
    this.props.uiActions.setLocale(lang);
  }

  getIntlProviderData = () => {
    const lang = this.props.lang;
    return {
      locale: lang,
      messages: messages[lang],
    };
  }

  render() {
    return (
      <DynamicProvider dynamic={this.props.dynamic}>
        <Provider store={this.props.store}>
          <IntlProvider {...this.getIntlProviderData()}>
              {this.props.children}
          </IntlProvider>
        </Provider>
      </DynamicProvider>
    );
  }
}

function mapStateToProps(state, props) {
  return {
    locale: getLocale(state),
  }
}

function mapDispatchToProps(dispatch) {
  return {
    uiActions: bindActionCreators(UIActions, dispatch),
  }
}

export default connect(
    mapStateToProps,
    mapDispatchToProps
)(App)
