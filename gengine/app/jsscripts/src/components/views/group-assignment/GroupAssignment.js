import React, { Component } from 'react';
import { bindActionCreators } from "redux";
import { connectDynamic, generateID } from "../../../lib/swagger";
import URLService from "../../../service/URLService"

import _ from 'lodash';
import './groupAssignment.css';

class GroupAssignment extends Component {

    componentWillMount = () => {
      this.searchGroups();
      if(URLService.getQueryParameterAsInt("group")) {
        this.searchUsers();
      }
    }

    getSearchParams = () => {
      return {
        include_search: URLService.getQueryParameterAsString("group_search") || ""
      }
    }

    searchGroups = () => {
      setTimeout(() => {
        this.props.actions.groupsSearchListRequest(this.getSearchParams())
      })
    }

    handleGroupClick = (group) => {
        URLService.setQueryParameter("group", group.id);
        this.searchUsers();
    }

    handleUserClick = (user) => {
        URLService.setQueryParameter("user", user.id);
        //this.searchUsers();
    }

    searchUsers = () => {
        setTimeout(() => {
            this.usersInGroupSearchID = generateID();
            this.props.actions.usersSearchListRequest({
                requestID: this.usersInGroupSearchID,
                include_group_id: URLService.getQueryParameterAsInt("group"),
                include_search: URLService.getQueryParameterAsString("user_search") || ""
            })

            this.usersNotInGroupSearchID = generateID();
            this.props.actions.usersSearchListRequest({
              requestID: this.usersNotInGroupSearchID,
              exclude_group_id: URLService.getQueryParameterAsInt("group"),
              include_search: URLService.getQueryParameterAsString("user_search") || ""
            })
        })
    }

    handleGroupSearchChange = (ev) => {
        URLService.setQueryParameter("group_search", ev.target.value);
        this.searchGroups();
    }

    handleUserSearchChange = (ev) => {
        URLService.setQueryParameter("user_search", ev.target.value);
        this.searchUsers();
    }

    handleAddUser = (user,group) => {
      this.props.actions.groupsAddUserRequest({
        user_id: user.id,
        group_id: group.id
      })
    }

    handleRemoveUser = (user,group) => {

    }

    render = () => {
        console.log("rendering!")

        const groups = this.props.groupsData ? this.props.groupsData.latest.groups : null;
        const active_group_id = URLService.getQueryParameterAsInt("group");
        const active_group = _.find(groups, (group) => group.id == active_group_id);
        const not_active_groups = _.filter(groups, (group) => group.id != active_group_id);

        const usersInGroup = this.props.usersData && this.props.usersData[this.usersInGroupSearchID] ? this.props.usersData[this.usersInGroupSearchID].users : null;
        const usersNotInGroup = this.props.usersData && this.props.usersData[this.usersNotInGroupSearchID] ? this.props.usersData[this.usersNotInGroupSearchID].users : null;

        console.log("props",this.props);
        console.log("groups",groups);
        console.log("usersInGroup",usersInGroup);
        console.log("usersNotInGroup",usersNotInGroup);

        return (
          <table className="group-assignment">
              <tbody><tr>
              <td className="groups">
                  <div className="side-header">
                      <div className="search-field-wrapper">
                        <i className="fa fa-search"></i>
                        <input className="search-field" type="text" placeholder="Search Groups" onChange={(ev) => this.handleGroupSearchChange(ev)} value={URLService.getQueryParameterAsString("group_search") || ""} />
                      </div>
                  </div>
                  <div className="groups-list">
                      {(active_group!=null) ? (
                        <div key={active_group.id} className="groups-list-item groups-list-item-selected" onClick={() => this.handleGroupClick(active_group)}>
                          ➡{active_group.name}
                        </div>
                      ):null}
                      {not_active_groups && not_active_groups.length>0 ? _.map(not_active_groups, (group)=> {
                          return (
                              <div key={group.id} className="groups-list-item" onClick={() => this.handleGroupClick(group)}>
                                  {group.name}
                              </div>
                          );
                      }) : null}
                  </div>
              </td>
              <td className="users">
                <div className="side-header">
                  <div className="search-field-wrapper">
                    <i className="fa fa-search"></i>
                    <input className="search-field" type="text" placeholder="Search Users" onChange={(ev) => this.handleUserSearchChange(ev)} value={URLService.getQueryParameterAsString("user_search") || ""} />
                  </div>
                </div>
                {active_group!=null ? (
                  <div className="user-list">
                    <div className="contained-user-list">
                      {usersInGroup && usersInGroup.length>0 ? (
                        <div className="contained-user-list-header">Users in {active_group.name}:</div>
                      ):null}
                      {usersInGroup && usersInGroup.length>0 ? _.map(usersInGroup, (user)=> {
                          return (
                              <div key={user.id} className="users-list-item" onClick={() => this.handleUserClick(user)}>
                                  {user.name}
                                  <div onClick={() => this.handleRemoveUser(user, active_group)} className="users-list-item-toggle">Remove</div>
                              </div>
                          );
                      }) : null}
                    </div>
                    <div className="not-contained-user-list">
                      {usersNotInGroup && usersNotInGroup.length>0 ? (
                        <div className="not-contained-user-list-header">Users not in {active_group.name}:</div>
                      ):null}
                      {usersNotInGroup && usersNotInGroup.length>0 ? _.map(usersNotInGroup, (user)=> {
                          return (
                            <div key={user.id} className="users-list-item" onClick={() => this.handleUserClick(user)}>
                              {user.name}
                              <div onClick={() => this.handleAddUser(user, active_group)} className="users-list-item-toggle">Add</div>
                            </div>
                          );
                        }) : null}
                    </div>
                  </div>
                ):(
                  <div>
                    Please select a Group.
                  </div>
                  )}
              </td>
              </tr></tbody>
          </table>
        )

    }
}

export default connectDynamic((dynamic, state, props) => {
  return {
    groupsData: dynamic.api.selectors.getGroupsSearchListData(state.api),
    usersData: dynamic.api.selectors.getUsersSearchListData(state.api),
    //echoLoading: dynamic.api.selectors.getDefaultEchoTestLoading(state.api),
    //echoError: dynamic.api.selectors.getDefaultEchoTestError(state.api)
  }
},(dynamic, dispatch, props) => {
  return {
    actions: bindActionCreators(dynamic.api.actions, dispatch)
  }
})(GroupAssignment)
