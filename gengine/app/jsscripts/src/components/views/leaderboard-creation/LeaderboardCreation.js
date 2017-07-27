import React, { Component } from 'react';
import { bindActionCreators } from "redux";
import { connectDynamic, generateID } from "../../../lib/swagger";
import URLService from "../../../service/URLService"
import InputMoment from 'input-moment';
import 'react-fontawesome';
import moment from 'moment';

import _ from 'lodash';
import './leaderboardCreation.css';

import Select from 'react-select';

class LeaderboardCreation extends Component {

  constructor() {
    super();
    this.domainsSearchID  = "DOMAINS_SEARCH";
  }

  componentWillMount = () => {
    this.props.actions.subjecttypesSearchListRequest({});
    this.props.actions.variablesSearchListRequest({});
    this.props.actions.timezonesListRequest({});
    this.props.actions.subjectsSearchListRequest({
      exclude_leaves: true,
      requestID: this.domainsSearchID
    });
  }

  getSubjectTypes = () => {
    if(this.props.subjecttypes && this.props.subjecttypes.latest && this.props.subjecttypes.latest.subjecttypes) {
      return this.props.subjecttypes.latest.subjecttypes;
    }
    return [];
  }

  getDomains = () => {
    if(this.props.subjects && this.props.subjects[this.domainsSearchID] && this.props.subjects[this.domainsSearchID].subjects) {
      return this.props.subjects.latest.subjects;
    }
    return [];
  }

  getVariables = () => {
    if(this.props.variables && this.props.variables.latest && this.props.variables.latest.variables) {
      return this.props.variables.latest.variables;
    }
    return [];
  }

  getTimezones = () => {
    if(this.props.timezones && this.props.timezones.latest && this.props.timezones.latest.timezones) {
      return this.props.timezones.latest.timezones;
    }
    return [];
  }

  /* Player */

  handlePlayerChange = (p) => {
    if(p !== null) {
      URLService.setQueryParameter("player", p.value);
    } else {
      URLService.removeQueryParameter("player");
    }
    this.setState({})
  }

  getPlayerOptions = () => {
    return _.map(this.getSubjectTypes(), (st) => {
      return {
        value: st.id,
        label: st.name
      }
    })
  }

  getSelectedPlayer = (p) => {
    return URLService.getQueryParameterAsInt("player");
  }

  /* Context */

  handleContextChange = (p) => {
    if(p !== null) {
      URLService.setQueryParameter("context", p.value);
    } else {
      URLService.removeQueryParameter("context");
    }
    this.setState({})
  }

  getContextOptions = () => {
    return _.map(this.getSubjectTypes(), (st) => {
      return {
        value: st.id,
        label: st.name
      }
    })
  }

  getSelectedContext = (p) => {
    return URLService.getQueryParameterAsInt("context");
  }

  /* Domains */

  handleDomainsChange = (domains) => {
    URLService.removeQueryParameter("domain");
    for(let d of domains) {
      URLService.addQueryParameter("domain", d.value);
    }
    this.setState({})
  }

  getDomainOptions = () => {
    return _.map(this.getDomains(), (st) => {
      return {
        value: st.id,
        label: st.name
      }
    })
  }

  getSelectedDomains = (p) => {
    return URLService.getQueryParameterValueAsIntList("domain");
  }

  /* Name */

  handleNameChange = (ev) => {
    let val = ev.target.value;
    URLService.setQueryParameter("name", val);
    this.setState({});
  }

  getName = () => {
    return URLService.getQueryParameterAsString("name","");
  }

  /* Variable */

  handleVariableChange = (p) => {
    if(p !== null) {
      URLService.setQueryParameter("variable", p.value);
    } else {
      URLService.removeQueryParameter("variable");
    }
    this.setState({})
  }

  getVariableOptions = () => {
    return _.map(this.getVariables(), (st) => {
      return {
        value: st.id,
        label: st.name
      }
    })
  }

  getSelectedVariable = (p) => {
    return URLService.getQueryParameterAsInt("variable");
  }

  /* Recurrence */

  handleRecurrenceChange = (p) => {
    if(p !== null) {
      URLService.setQueryParameter("recurrence", p.value);
    } else {
      URLService.removeQueryParameter("recurrence");
    }
    this.setState({})
  }

  getRecurrenceOptions = () => {
    return [{
      value: "immediately",
      label: "No"
    },{
      value: "daily",
      label: "Daily"
    },{
      value: "weekly",
      label: "Weekly"
    },{
      value: "monthly",
      label: "Monthly"
    },{
      value: "yearly",
      label: "Yearly"
    },]
  }

  getSelectedRecurrence = (p) => {
    return URLService.getQueryParameterAsString("recurrence","immediately");
  }

  /* Timezones */

  handleTimezoneChange = (p) => {
    if(p !== null) {
      URLService.setQueryParameter("timezone", p.value);
    } else {
      URLService.removeQueryParameter("timezone");
    }
    this.setState({})
  }

  getTimezoneOptions = () => {
    return _.map(this.getTimezones(), (st) => {
      return {
        value: st.name,
        label: st.name
      }
    })
  }

  getSelectedTimezone = (p) => {
    return URLService.getQueryParameterAsString("timezone","US/Eastern");
  }

  /* First day of a week (FDW) */

  handleFDWChange = (p) => {
    if(p !== null) {
      URLService.setQueryParameter("fdw", p.value);
    } else {
      URLService.removeQueryParameter("fdw");
    }
    this.setState({})
  }

  getFDWOptions = () => {
    return [{
      'value': 'monday',
      'label': 'Monday'
    },{
      'value': 'tuesday',
      'label': 'Tuesday'
    },{
      'value': 'wednesday',
      'label': 'Wednesday'
    },{
      'value': 'thursday',
      'label': 'Thursday'
    },{
      'value': 'friday',
      'label': 'Friday'
    },{
      'value': 'saturday',
      'label': 'Saturday'
    },{
      'value': 'sunday',
      'label': 'Sunday'
    }]
  }

  getSelectedFDW = (p) => {
    return URLService.getQueryParameterAsString("fdw","monday");
  }

  fdwToShift = () => {
    const fdw = this.getSelectedFDW()
    if(fdw == "monday") {
      return 0;
    }
    if(fdw == "tuesday") {
      return (- 6 * 24 * 60 * 60);
    }
    if(fdw == "wednesday") {
      return (- 5 * 24 * 60 * 60);
    }
    if(fdw == "thursday") {
      return (- 4 * 24 * 60 * 60);
    }
    if(fdw == "friday") {
      return (- 3 * 24 * 60 * 60);
    }
    if(fdw == "saturday") {
      return (- 2 * 24 * 60 * 60);
    }
    if(fdw == "sunday") {
      return (- 1 * 24 * 60 * 60);
    }
  }

  /* Valid timespan */

  getSelectedSpecifyTimespan = () => {
    return URLService.getQueryParameterAsBool("ts") || false;
  }

  handleSpecifyTimespanChange = (ev) => {
    URLService.toggleQueryParameter("ts","1");
    this.setState({})
  }

  getSelectedValidEnd = () => {
    const s = URLService.getQueryParameterAsString("validEnd",null);
    if(s) {
      return moment(s);
    } else {
      return moment().add(1,'months')
    }
  }

  getSelectedValidStart = () => {
    const s = URLService.getQueryParameterAsString("validStart",null);
    if(s) {
      return moment(s);
    } else {
      return moment()
    }
  }

  handleValidStartChange = (d) => {
    URLService.setQueryParameter("validStart", d.format("YYYY-MM-DD"))
    this.setState({})
  }

  handleValidEndChange = (d) => {
    URLService.setQueryParameter("validEnd", d.format("YYYY-MM-DD"))
    this.setState({})
  }

  handleCreateClick = () => {
    const variable = _.find(this.getVariables(), (v) => v.id==this.getSelectedVariable());
    this.props.actions.createAchievementRequest({
        'name': this.getName(),
        'player_subjecttype_id': this.getSelectedPlayer(),
        'comparison_type': this.getSelectedContext() ? 'context_subject' : 'global',
        'context_subjecttype_id': this.getSelectedContext(),
        'domain_subject_ids': this.getSelectedDomains(),
        'condition': {
          "term": {
            "type": "literal",
            "variable": variable.name
          }
        },
        'evaluation': this.getSelectedRecurrence(),
        'evaluation_timezone': this.getSelectedTimezone(),
        'evaluation_shift': this.fdwToShift(),
        'valid_start': this.getSelectedSpecifyTimespan() ? this.getSelectedValidStart() : null,
        'valid_end': this.getSelectedSpecifyTimespan() ? this.getSelectedValidEnd() : null,
    })
  }

  render = () => {
    console.log("props", this.props)

    if(this.props.createData && this.props.createData.latest && this.props.createData.latest.status == "ok") {
      // creation okay
      return (
        <div className="leaderboard-creation">
          <div className="alert alert-success">Leaderboard created successfully</div>
        </div>
      );
    } else if(this.props.createError && this.props.createError[0]) {
      // creation okay
      return (
        <div className="leaderboard-creation">
          <div className="alert alert-error">Error: {this.props.createError[0].errorData.message}</div>
        </div>
      );
    } else {
      return (
        <div className="leaderboard-creation">
          <div className="form-row">
            <div className="form-row-label">
              Name
            </div>
            <div className="form-row-field">
              <input type="text" name="name" value={this.getName()} onChange={this.handleNameChange} />
            </div>
            <div className="form-row-description">
              Please give me a unique name
            </div>
          </div>
          <div className="form-row">
            <div className="form-row-label">
              Players
            </div>
            <div className="form-row-field">
              <Select
                name="player"
                value={this.getSelectedPlayer()}
                options={this.getPlayerOptions()}
                onChange={this.handlePlayerChange}
                placeholder="Player"
              />
            </div>
            <div className="form-row-description">
              Who are the players of the leaderboard?
            </div>
          </div>


          <div className="form-row">
            <div className="form-row-label">
              Context
            </div>
            <div className="form-row-field">
              <Select
                name="context"
                value={this.getSelectedContext()}
                options={this.getContextOptions()}
                onChange={this.handleContextChange}
                placeholder="Context"
              />
            </div>
            <div className="form-row-description">
              The players are compared with other players in a specific context (e.g. a country).
            </div>
          </div>

          <div className="form-row">
            <div className="form-row-label">
              Domain
            </div>
            <div className="form-row-field">
              <Select
                name="domain"
                value={this.getSelectedDomains()}
                options={this.getDomainOptions()}
                onChange={this.handleDomainsChange}
                multi={true}
                placeholder="Domain"
              />
            </div>
            <div className="form-row-description">
              The game can be restricted to specific subjects (e.g. only participants in a specific team).
            </div>
          </div>

          <div className="form-row">
            <div className="form-row-label">
              Variable
            </div>
            <div className="form-row-field">
              <Select
                name="variable"
                value={this.getSelectedVariable()}
                options={this.getVariableOptions()}
                onChange={this.handleVariableChange}
                placeholder="Variable"
              />
            </div>
            <div className="form-row-description">
              Please select the variable which is used for this leaderboard.
            </div>
          </div>

          <div className="form-row">
            <div className="form-row-label">
              Recurrence
            </div>
            <div className="form-row-field">
              <Select
                name="recurrence"
                value={this.getSelectedRecurrence()}
                options={this.getRecurrenceOptions()}
                onChange={this.handleRecurrenceChange}
                placeholder="Recurrence"
              />
            </div>
            <div className="form-row-description">
              Do you want to reset the leaderboard from time to time?
            </div>
          </div>

          <div className="form-row">
            <div className="form-row-label">
              Timezone
            </div>
            <div className="form-row-field">
              <Select
                name="timezone"
                value={this.getSelectedTimezone()}
                options={this.getTimezoneOptions()}
                onChange={this.handleTimezoneChange}
                placeholder="Timezone"
              />
            </div>
            <div className="form-row-description">
              If you make time-related settings, it's important to agree on a timezone.
            </div>
          </div>

          <div className="form-row">
            <div className="form-row-label">
              First day of a week
            </div>
            <div className="form-row-field">
              <Select
                name="firstdayofweek"
                value={this.getSelectedFDW()}
                options={this.getFDWOptions()}
                onChange={this.handleFDWChange}
                placeholder="First day of a week"
              />
            </div>
            <div className="form-row-description">
              Please select the first day of a week.
            </div>
          </div>

          <div className="form-row">
            <div className="form-row-label">
              Valid time span
            </div>
            <div className="form-row-field">
              <div className="timespan-cb">
                <input id="ts" type="checkbox" onChange={this.handleSpecifyTimespanChange} checked={this.getSelectedSpecifyTimespan()} />
                <span onClick={this.handleSpecifyTimespanChange}>Specify time span</span>
              </div>
              {(this.getSelectedSpecifyTimespan() ? (
                <div>
                  <div className="span-6">
                    <b>Start</b><br />
                    <InputMoment
                      moment={this.getSelectedValidStart()}
                      onChange={this.handleValidStartChange}
                      prevMonthIcon="fa fa-chevron-left"
                      nextMonthIcon="fa fa-chevron-right"
                    />
                  </div>
                  <div className="span-6">
                    <b>End</b><br />
                    <InputMoment
                      moment={this.getSelectedValidEnd()}
                      onChange={this.handleValidEndChange}
                      prevMonthIcon="fa fa-chevron-left"
                      nextMonthIcon="fa fa-chevron-right"
                    />
                  </div>
                </div>
              ) : '')}
            </div>
            <div className="form-row-description">
              You can restrict the leaderboard to be only active for a specific time span.
            </div>
          </div>

          <div className="form-row">
            <div className="control-group">
              <div className="controls">
                <button type="button" className="btn btn-primary" onClick={this.handleCreateClick}>Create</button>
              </div>
            </div>
          </div>
        </div>
      )
    }
  }
}

export default connectDynamic((dynamic, state, props) => {
  return {
    subjecttypes: dynamic.api.selectors.getSubjecttypesSearchListData(state.api),
    subjects: dynamic.api.selectors.getSubjectsSearchListData(state.api),
    variables: dynamic.api.selectors.getVariablesSearchListData(state.api),
    timezones: dynamic.api.selectors.getTimezonesListData(state.api),
    createData: dynamic.api.selectors.getCreateAchievementData(state.api),
    createError: dynamic.api.selectors.getCreateAchievementError(state.api),
  }
},(dynamic, dispatch, props) => {
  return {
    actions: bindActionCreators(dynamic.api.actions, dispatch)
  }
})(LeaderboardCreation)
