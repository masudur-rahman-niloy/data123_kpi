import React from 'react';
import autoBind from 'react-autobind';
import Checkbox from 'js/components/common/checkbox';
import {actions} from 'js/actions';
import bem from 'js/bem';
import permConfig from 'js/components/permissions/permConfig';
import {buildUserUrl} from 'utils';
import {
  ROOT_URL,
  ANON_USERNAME,
  PERMISSIONS_CODENAMES,
} from 'js/constants';

class PublicShareSettings extends React.Component {
  constructor(props) {
    super(props);
    autoBind(this);
    this.anonCanViewPermUrl = permConfig.getPermissionByCodename(PERMISSIONS_CODENAMES.view_asset).url;
    this.anonCanViewDataPermUrl = permConfig.getPermissionByCodename(PERMISSIONS_CODENAMES.view_submissions).url;
    this.anonCanAddDataPermUrl = permConfig.getPermissionByCodename(PERMISSIONS_CODENAMES.add_submissions).url;
  }
  togglePerms(permCodename) {
    var permission = this.props.publicPerms.filter((perm) => {
      return perm.permission === permConfig.getPermissionByCodename(permCodename).url;
    })[0];
    if (permission) {
      actions.permissions.removeAssetPermission(this.props.uid, permission.url);
    } else {
      actions.permissions.assignAssetPermission(
        this.props.uid, {
          user: buildUserUrl(ANON_USERNAME),
          permission: permConfig.getPermissionByCodename(permCodename).url
        }
      );
    }
  }
  render () {
    const uid = this.props.uid;
    const url = `${ROOT_URL}/#/forms/${uid}`;

    const anonCanView = this.props.publicPerms.filter((perm) => {return perm.permission === this.anonCanViewPermUrl;})[0];
    const anonCanViewData = this.props.publicPerms.filter((perm) => {return perm.permission === this.anonCanViewDataPermUrl;})[0];
    const anonCanAddData = this.props.publicPerms.filter((perm) => {return perm.permission === this.anonCanAddDataPermUrl;})[0];

    return (
      <bem.FormModal__item m='permissions'>
        <bem.FormModal__item>
          <Checkbox
            checked={anonCanView ? true : false}
            onChange={this.togglePerms.bind(this, 'view_asset')}
            label={t('Anyone can view this form')}
          />
        </bem.FormModal__item>

        { this.props.deploymentActive &&
          <bem.FormModal__item>
            <Checkbox
              checked={anonCanViewData ? true : false}
              onChange={this.togglePerms.bind(this, 'view_submissions')}
              label={t('Anyone can view submissions made to this form')}
            />
          </bem.FormModal__item>
        }

        { anonCanView &&
          <bem.FormModal__item m='shareable-link'>
            <label>
              {t('Shareable link')}
            </label>
            <input type='text' value={url} readOnly />
          </bem.FormModal__item>
        }

        { this.props.deploymentActive &&
          <bem.FormModal__item>
            <Checkbox
              checked={anonCanAddData ? true : false}
              onChange={this.togglePerms.bind(this, 'add_submissions')}
              label={t('Anyone can ADD data to this form')}
            />
          </bem.FormModal__item>
        }
      </bem.FormModal__item>
    );
  }
}

export default PublicShareSettings;
