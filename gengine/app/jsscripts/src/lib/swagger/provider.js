import React, {Component, PropTypes, Children} from 'react';
import invariant from 'invariant';
import { connect } from 'react-redux';

export class DynamicProvider extends Component {

    static propTypes = {
        dynamic: PropTypes.object,
    };

    static childContextTypes = {
        dynamic: PropTypes.object,
    };

    getChildContext() {
        return {
            dynamic: this.props.dynamic
        }
    }

    render() {
        return Children.only(this.props.children);
    }
}

function getDisplayName(Component) {
    return Component.displayName || Component.name || 'Component';
}

function invariantDynamicContext({dynamic} = {}) {
    invariant(dynamic,
        '[Redux Swagger] Could not find required `dynamic` object. ' +
        '<DynamicProvider> needs to exist in the component ancestry.'
    );
}

export function connectDynamic(mapStateToProps, mapDispatchToProps) {
    return function(WrappedComponent, options = {}) {
        const {
            withRef      = false,
        } = options;

        class DynamicConnected extends Component {
            static displayName = `DynamicConnected(${getDisplayName(WrappedComponent)})`;

            static contextTypes = {
                dynamic: PropTypes.object,
                store: PropTypes.object
            };

            constructor(props, context) {
                super(props, context);
                invariantDynamicContext(context);

                let dynamic = this.context.dynamic;
                let state = this.context.store.getState();
                let dispatch = this.context.store.dispatch;

                this.WrappedComponent = connect(function(state, props) {
                    return mapStateToProps(dynamic, state, props)
                }, function(dispatch, props) {
                    return mapDispatchToProps(dynamic, dispatch, props)
                })(WrappedComponent);
            }

            getWrappedInstance() {
                invariant(withRef,
                    '[Redux Swagger] To access the wrapped instance, ' +
                    'the `{withRef: true}` option must be set when calling: ' +
                    '`connectDynamic()`'
                );

                return this.refs.wrappedInstance;
            }

            render() {
                return (
                    <this.WrappedComponent {...this.props} ref={withRef ? 'wrappedInstance' : null} />
                )
            }
        }

        return DynamicConnected
    }
}


