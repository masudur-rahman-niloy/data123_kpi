import React from 'react';
import autoBind from 'react-autobind';
import bem from 'js/bem';
import sessionStore from 'js/stores/session';
import DocumentTitle from 'react-document-title';
import ProjectExportsCreator from 'js/components/projectDownloads/projectExportsCreator';
import ProjectExportsList from 'js/components/projectDownloads/projectExportsList';
import LegacyExports from 'js/components/projectDownloads/legacyExports';
import AnonymousExports from 'js/components/projectDownloads/anonymousExports';
import exportsStore from 'js/components/projectDownloads/exportsStore';

/**
 * This is the ROUTES.FORM_DOWNLOADS route component. It will check whether the
 * user is logged in or not and display proper child components.
 *
 * @prop {object} asset
 */
export default class ProjectDownloads extends React.Component {
  constructor(props){
    super(props);
    this.state = {selectedExportType: exportsStore.getExportType()};
    this.unlisteners = [];
    autoBind(this);
  }

  componentDidMount() {
    this.unlisteners.push(
      exportsStore.listen(this.onExportsStoreChange),
    );
  }

  componentWillUnmount() {
    this.unlisteners.forEach((clb) => {clb();});
  }

  onExportsStoreChange() {
    this.setState({selectedExportType: exportsStore.getExportType()});
  }

  renderLoggedInExports() {
    if (this.state.selectedExportType.isLegacy) {
      return (
        <LegacyExports asset={this.props.asset} />
      );
    } else {
      return (
        <React.Fragment>
          <ProjectExportsCreator asset={this.props.asset}/>
          <ProjectExportsList asset={this.props.asset}/>
        </React.Fragment>
      );
    }
  }

  render() {
    var docTitle = this.props.asset.name || t('Untitled');
    return (
      <DocumentTitle title={`${docTitle} | Data 123`}>
        <bem.FormView className='project-downloads'>
          <bem.FormView__row>
            <bem.FormView__cell m={['page-title']}>
              {t('Downloads')}
            </bem.FormView__cell>

            {sessionStore.isLoggedIn &&
              this.renderLoggedInExports()
            }

            {!sessionStore.isLoggedIn &&
              <AnonymousExports asset={this.props.asset}/>
            }
          </bem.FormView__row>
        </bem.FormView>
      </DocumentTitle>
    );
  }
}
