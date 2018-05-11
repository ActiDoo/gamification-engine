import React, { Component } from 'react';
import { bindActionCreators } from "redux";
import { connectDynamic, generateID } from "../../../lib/swagger";
import URLService from "../../../service/URLService"

import _ from 'lodash';
import './groupAssignment.css';

class GroupAssignment extends Component {

    constructor() {
        super();
        this.parentsSearchID = "GROUP_ASSIGNMENT_PARENTS";
        this.usersInGroupSearchID = "GROUP_ASSIGNMENT_IN_GROUP";
        this.usersNotInGroupSearchID = "GROUP_ASSIGNMENT_NOT_IN_GROUP";
    }

    componentWillMount = () => {
      this.searchParents();
      if(URLService.getQueryParameterAsString("parent_id")) {
        this.searchSubjects();
      }
    }

    getSearchParams = () => {
      return {
        include_search: URLService.getQueryParameterAsString("parent_search") || "",
        exclude_leaves: true,
        requestID: this.parentsSearchID
      }
    }

    searchParents = () => {
      setTimeout(() => {
        this.props.actions.subjectsSearchListRequest(this.getSearchParams())
      })
    }

    handleParentClick = (parent_id, subjecttype_id) => {
        URLService.setQueryParameter("parent_id", ""+parent_id+"-"+subjecttype_id);
        this.searchSubjects();
    }

    handleSubjectClick = (subject_id) => {
        URLService.setQueryParameter("subject", subject_id);
        //this.searchSubjects();
    }

    searchSubjects = () => {
        setTimeout(() => {
	        this.props.actions.subjectsSearchListRequest({
                requestID: this.usersInGroupSearchID,
                parent_subjecttype_id: parseInt(URLService.getQueryParameterAsString("parent_id", "-").split("-")[1]),
                parent_subject_id: parseInt(URLService.getQueryParameterAsString("parent_id", "-").split("-")[0]),
                include_search: URLService.getQueryParameterAsString("subject_search") || "",
            })
        })
    }

    handleParentSearchChange = (ev) => {
        URLService.setQueryParameter("parent_search", ev.target.value);
        this.searchParents();
    }

    handleSubjectSearchChange = (ev) => {
        URLService.setQueryParameter("subject_search", ev.target.value);
        this.searchSubjects();
    }

    handleAddSubject = (subject, parent) => {
      this.props.actions.subjectsAddToParentRequest({
        subject_id: subject.id,
        parent_id: parent.id
      })
	    subject.in_parent=true;
      this.setState({})
    }

    handleRemoveSubject = (subject, parent) => {
	    this.props.actions.subjectsRemoveFromParentRequest({
		    subject_id: subject.id,
		    parent_id: parent.id
	    })
	    subject.in_parent=false;
	    this.setState({})
    }

    renderSubjectRow = (subject, active_parent) => {
        return (
            <div key={subject.id} className="users-list-item" onClick={() => this.handleSubjectClick(subject.id)}>
                {subject.name}
                {subject.inherited_by ? (
                    <span> (inherited by <span className="inherited-group-link" onClick={() => this.handleParentClick(subject.inherited_by, subject.inherited_by_subjecttype_id)}>{subject.inherited_by_name})</span></span>
                ) : (
                    subject.in_parent ? (
                            <div onClick={() => this.handleRemoveSubject(subject, active_parent)} className="users-list-item-toggle">Remove</div>
                    ) : (
                        <div onClick={() => this.handleAddSubject(subject, active_parent)} className="users-list-item-toggle">Add</div>
                    )

                )}
            </div>
        )
    }

    render = () => {
        console.log("rendering!")
        const searchData = this.props.searchData || {};

        const parents = searchData[this.parentsSearchID] ? searchData[this.parentsSearchID].subjects : null;
        const active_parent_id = URLService.getQueryParameterAsString("parent_id", "").split("-")[0];
        const active_parent = _.find(parents, (p) => p.id == active_parent_id);
        const not_active_parents = _.filter(parents, (p) => p.id != active_parent_id);

        const possibleSubjects = searchData[this.usersInGroupSearchID] ? searchData[this.usersInGroupSearchID].subjects : null;
	      const subjectsInParent = _.filter(possibleSubjects, (s) => s.in_parent);
	      const subjectsNotInParent = _.filter(possibleSubjects, (s) => !s.in_parent);
	    /*_.each(subjectsInParent,(user) => {
			if(!user.directly_in_parent) {
				const pathItems = _.split(user.path, "->");
				_.each(pathItems, (pathItem) => {
					if(pathItem == active_parent_id) {
						user.groupInheritedBy = ug;
					}
				})
			}
		})*/
        /*const usersNotInGroup = this.props.usersData && this.props.usersData[this.usersNotInGroupSearchID] ? this.props.usersData[this.usersNotInGroupSearchID].users : null;
        _.each(usersNotInGroup,(user) => {
            if(typeof user.isInGroup == 'undefined') {
                user.isInGroup = false;
            }
        })*/

        console.log("props",this.props);
        console.log("groups",parents);
        console.log("usersInGroup",subjectsInParent);
        console.log("usersNotInGroup",subjectsNotInParent);

        return (
          <table className="group-assignment">
              <tbody><tr>
              <td className="groups">
                  <div className="side-header">
                      <div className="search-field-wrapper">
                        <i className="fa fa-search"></i>
                        <input className="search-field" type="text" placeholder="Search Groups" onChange={(ev) => this.handleParentSearchChange(ev)} value={URLService.getQueryParameterAsString("parent_search") || ""} />
                      </div>
                  </div>
                  <div className="groups-list">
                      {(active_parent!=null) ? (
                        <div key={active_parent.id} className="groups-list-item groups-list-item-selected" onClick={() => this.handleParentClick(active_parent.id, active_parent.subjecttype_id)}>
                          ➡{active_parent.name}
                        </div>
                      ):null}
                      {not_active_parents && not_active_parents.length>0 ? _.map(not_active_parents, (group)=> {
                          return (
                              <div key={group.id} className="groups-list-item" onClick={() => this.handleParentClick(group.id, group.subjecttype_id)}>
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
                    <input className="search-field" type="text" placeholder="Search Users" onChange={(ev) => this.handleSubjectSearchChange(ev)} value={URLService.getQueryParameterAsString("subject_search") || ""} />
                  </div>
                </div>
                {active_parent!=null ? (
                  <div className="user-list">
                    <div className="contained-user-list">
                      {subjectsInParent && subjectsInParent.length>0 ? (
                        <div className="contained-user-list-header">Subjects in {active_parent.name}:</div>
                      ):null}
                      {subjectsInParent && subjectsInParent.length>0 ? _.map(subjectsInParent, (user)=> {
                          return this.renderSubjectRow(user, active_parent)
                      }) : null}
                    </div>
                    <div className="not-contained-user-list">
                      {subjectsNotInParent && subjectsNotInParent.length>0 ? (
                        <div className="not-contained-user-list-header">Subjects not in {active_parent.name}:</div>
                      ):null}
                      {subjectsNotInParent && subjectsNotInParent.length>0 ? _.map(subjectsNotInParent, (user)=> {
                          return this.renderSubjectRow(user, active_parent)
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
    searchData: dynamic.api.selectors.getSubjectsSearchListData(state.api),
    //echoLoading: dynamic.api.selectors.getDefaultEchoTestLoading(state.api),
    //echoError: dynamic.api.selectors.getDefaultEchoTestError(state.api)
  }
},(dynamic, dispatch, props) => {
  return {
    actions: bindActionCreators(dynamic.api.actions, dispatch)
  }
})(GroupAssignment)
