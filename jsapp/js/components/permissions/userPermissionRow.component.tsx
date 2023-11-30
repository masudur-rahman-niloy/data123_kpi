import React from 'react';
import alertify from 'alertifyjs';
import assetStore from 'js/assetStore';
import {actions} from 'js/actions';
import bem from 'js/bem';
import {stringToColor, escapeHtml} from 'js/utils';
import UserAssetPermsEditor from './userAssetPermsEditor.component';
import permConfig from './permConfig';
import type {UserPerm} from './permParser';
import type {PermissionBase} from 'js/dataInterface';
import type {AssignablePermsMap} from './sharingForm.component';
import {getPermLabel, getFriendlyPermName} from './utils';

interface UserPermissionRowProps {
  assetUid: string;
  nonOwnerPerms: PermissionBase[];
  assignablePerms: AssignablePermsMap;
  permissions: UserPerm[];
  isUserOwner: boolean;
  username: string;
}

interface UserPermissionRowState {
  isEditFormVisible: boolean;
  isBeingDeleted: boolean;
}

export default class UserPermissionRow extends React.Component<
  UserPermissionRowProps,
  UserPermissionRowState
> {
  constructor(props: UserPermissionRowProps) {
    super(props);

    this.state = {
      isEditFormVisible: false,
      isBeingDeleted: false,
    };
  }

  componentDidMount() {
    assetStore.listen(this.onAssetChange, this);
  }

  onAssetChange() {
    // fixes bug that disables a user who was re-added after being deleted
    this.setState({isBeingDeleted: false});
  }

  showRemovePermissionsPrompt() {
    const dialog = alertify.dialog('confirm');
    const opts = {
      title: t('Remove permissions?'),
      message: t(
        'This action will remove all permissions for user ##username##'
      ).replace(
        '##username##',
        `<strong>${escapeHtml(this.props.username)}</strong>`
      ),
      labels: {ok: t('Remove'), cancel: t('Cancel')},
      onok: this.removeAllPermissions.bind(this),
      oncancel: dialog.destroy,
    };
    dialog.set(opts).show();
  }

  /**
   * Note: we remove "view_asset" permission, as it is the most basic one,
   * so removing it will in fact remove all permissions
   */
  removeAllPermissions() {
    this.setState({isBeingDeleted: true});
    const userViewAssetPerm = this.props.permissions.find(
      (perm) =>
        perm.permission ===
        permConfig.getPermissionByCodename('view_asset')?.url
    );
    if (userViewAssetPerm) {
      actions.permissions.removeAssetPermission(
        this.props.assetUid,
        userViewAssetPerm.url
      );
    }
  }

  onPermissionsEditorSubmitEnd(isSuccess: boolean) {
    if (isSuccess) {
      this.setState({isEditFormVisible: false});
    }
  }

  toggleEditForm() {
    this.setState({isEditFormVisible: !this.state.isEditFormVisible});
  }

  /**
   * Note that this renders partial permission using a general label with a list
   * of related conditions.
   */
  renderPermissions(permissions: UserPerm[]) {
    return (
      <bem.UserRow__perms>
        {permissions.map((perm) => {
          const permLabel = getPermLabel(perm);

          const friendlyPermName = getFriendlyPermName(perm);

          return (
            <bem.UserRow__perm key={permLabel}>
              {friendlyPermName}
            </bem.UserRow__perm>
          );
        })}
      </bem.UserRow__perms>
    );
  }

  render() {
    const initialsStyle = {
      background: `#${stringToColor(this.props.username)}`,
    };

    const modifiers = [];
    if (this.props.permissions.length === 0) {
      modifiers.push('deleted');
    }
    if (this.state.isBeingDeleted) {
      modifiers.push('pending');
    }

    return (
      <bem.UserRow m={modifiers}>
        <bem.UserRow__info>
          <bem.UserRow__avatar>
            <bem.AccountBox__initials style={initialsStyle}>
              {this.props.username.charAt(0)}
            </bem.AccountBox__initials>
          </bem.UserRow__avatar>

          <bem.UserRow__name>{this.props.username}</bem.UserRow__name>

          {this.props.isUserOwner && (
            <bem.UserRow__perms>{t('is owner')}</bem.UserRow__perms>
          )}
          {!this.props.isUserOwner && (
            <React.Fragment>
              {this.renderPermissions(this.props.permissions)}

              <bem.Button m='icon' onClick={this.toggleEditForm.bind(this)}>
                {this.state.isEditFormVisible && (
                  <i className='k-icon k-icon-close' />
                )}
                {!this.state.isEditFormVisible && (
                  <i className='k-icon k-icon-edit' />
                )}
              </bem.Button>

              <bem.Button m='icon' onClick={this.showRemovePermissionsPrompt.bind(this)}>
                <i className='k-icon k-icon-trash' />
              </bem.Button>
            </React.Fragment>
          )}
        </bem.UserRow__info>

        {this.state.isEditFormVisible && (
          <bem.UserRow__editor>
            <UserAssetPermsEditor
              assetUid={this.props.assetUid}
              username={this.props.username}
              permissions={this.props.permissions}
              assignablePerms={this.props.assignablePerms}
              nonOwnerPerms={this.props.nonOwnerPerms}
              onSubmitEnd={this.onPermissionsEditorSubmitEnd.bind(this)}
            />
          </bem.UserRow__editor>
        )}
      </bem.UserRow>
    );
  }
}
