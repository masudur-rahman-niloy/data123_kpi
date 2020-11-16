import React from 'react';
import reactMixin from 'react-mixin';
import autoBind from 'react-autobind';
import Reflux from 'reflux';
import PropTypes from 'prop-types';
import {bem} from 'js/bem';
import {stores} from 'js/stores';
import {hashHistory} from 'react-router';
import {t} from 'js/utils';
import {
  MODAL_TYPES,
  ASSET_TYPES
} from 'js/constants';
import mixins from 'js/mixins';
import ownedCollectionsStore from 'js/components/library/ownedCollectionsStore';

class LibraryNewItemForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      isSessionLoaded: !!stores.session.currentAccount
    };

    autoBind(this);
  }

  componentDidMount() {
    this.listenTo(stores.session, () => {
      this.setState({isSessionLoaded: true});
    });
  }

  goToAssetCreator() {
    stores.pageState.hideModal();

    let targetPath = '/library/asset/new';
    if (this.isLibrarySingle()) {
      const found = ownedCollectionsStore.find(this.currentAssetID());
      if (found && found.asset_type === ASSET_TYPES.collection.id) {
        // when creating from within a collection page, make the new asset
        // a child of this collection
        targetPath = `/library/asset/${found.uid}/new`;
      }
    }

    hashHistory.push(targetPath);
  }

  goToCollection() {
    stores.pageState.switchModal({
      type: MODAL_TYPES.LIBRARY_COLLECTION,
      previousType: MODAL_TYPES.LIBRARY_NEW_ITEM
    });
  }

  goToTemplate() {
    stores.pageState.switchModal({
      type: MODAL_TYPES.LIBRARY_TEMPLATE,
      previousType: MODAL_TYPES.LIBRARY_NEW_ITEM
    });
  }

  goToUpload() {
    stores.pageState.switchModal({
      type: MODAL_TYPES.LIBRARY_UPLOAD,
      previousType: MODAL_TYPES.LIBRARY_NEW_ITEM
    });
  }

  renderLoading(message = t('loading…')) {
    return (
      <bem.Loading>
        <bem.Loading__inner>
          <i />
          {message}
        </bem.Loading__inner>
      </bem.Loading>
    );
  }

  render() {
    if (!this.state.isSessionLoaded) {
      return this.renderLoading();
    }

    return (
      <bem.FormModal__form className='project-settings project-settings--form-source'>
        <bem.FormModal__item m='form-source-buttons'>
          <button onClick={this.goToAssetCreator}>
            <i className='k-icon-question-block' />
            {t('Question Block')}
          </button>

          <button onClick={this.goToTemplate}>
            <i className='k-icon-template' />
            {t('Template')}
          </button>

          <button onClick={this.goToUpload}>
            <i className='k-icon-upload' />
            {t('Upload')}
          </button>

          <button onClick={this.goToCollection}>
            <i className='k-icon-folder' />
            {t('Collection')}
          </button>
        </bem.FormModal__item>
      </bem.FormModal__form>
    );
  }
}

reactMixin(LibraryNewItemForm.prototype, Reflux.ListenerMixin);
reactMixin(LibraryNewItemForm.prototype, mixins.contextRouter);

LibraryNewItemForm.contextTypes = {
  router: PropTypes.object
};

export default LibraryNewItemForm;
