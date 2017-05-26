import React, { Component } from 'react';
import { bindActionCreators } from "redux";
import { connectDynamic } from "../../../lib/swagger";
import URLService from "../../../service/URLService"
import './groupAssignment.css';

class GroupAssignment extends Component {

    componentWillMount = () => {
      this.props.actions.usersSearchListRequest({body:this.getSearchParams()})
    }

    getSearchParams = () => {
      return {
        include_search: URLService.getQueryParameterAsString() || ""
      }
    }

    render = () => {

        return (
          <div className="group-assignment">
              <div className="users">
                <div className="side-header">Users</div>
              </div>
              <div className="groups">
                <div className="side-header">Groups</div>
              </div>
          </div>
        )

    }
}

export default connectDynamic((dynamic, state, props) => {
  return {
    o: state.api.data.o ? state.api.data.o : "",
    x: state.api.data.x ? state.api.data.x : "",
    //echoLoading: dynamic.api.selectors.getDefaultEchoTestLoading(state.api),
    //echoError: dynamic.api.selectors.getDefaultEchoTestError(state.api)
  }
},(dynamic, dispatch, props) => {
  return {
    actions: bindActionCreators(dynamic.api.actions, dispatch)
  }
})(GroupAssignment)
