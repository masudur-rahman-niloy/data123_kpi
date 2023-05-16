import React from 'react';
import autoBind from 'react-autobind';
import bem from 'js/bem';
import './radio.scss';

export interface RadioOption {
  label: string;
  value: string;
  /** Disables just this option. */
  isDisabled?: boolean;
}

interface RadioProps {
  options: RadioOption[];
  /** Displays a label/title on top of the radio options. */
  title?: string;
  /** Internal ID useful for the identification of radio. */
  name: string;
  onChange: (newSelectedValue: string, radioName: string) => void;
  /** The `value` of selected option. */
  selected: string;
  /** Disables whole radio component. */
  isDisabled?: boolean;
  /** This is `false` by default */
  isClearable?: boolean;
  'data-cy'?: string;
}

/** A radio input generic component. */
class Radio extends React.Component<RadioProps> {
  constructor(props: RadioProps){
    if (typeof props.onChange !== 'function') {
      throw new Error('onChange callback missing!');
    }
    super(props);
    autoBind(this);
  }

  onChange(evt: React.ChangeEvent<HTMLInputElement>) {
    this.props.onChange(evt.currentTarget.value, this.props.name);
  }

  onClick(evt: React.ChangeEvent<HTMLInputElement>) {
    // For clearable radio, we unselect checked option when clicked
    if (
      this.props.isClearable &&
      evt.currentTarget.checked
    ) {
      this.props.onChange('', this.props.name);
    }
  }

  render() {
    return (
      <bem.Radio m={{'disabled': Boolean(this.props.isDisabled)}}>
        {this.props.title &&
          <bem.Radio__row m='title'>{this.props.title}</bem.Radio__row>
        }
        {this.props.options.map((option) => (
            <bem.Radio__row key={option.value}>
              <bem.Radio__input
                type='radio'
                value={option.value}
                name={this.props.name}
                onChange={this.onChange.bind(this)}
                onClick={this.onClick.bind(this)}
                checked={this.props.selected === option.value}
                disabled={this.props.isDisabled || option.isDisabled}
                data-cy={this.props['data-cy']}
              />

              <bem.Radio__label>
                {option.label}
              </bem.Radio__label>
            </bem.Radio__row>
          ))}
      </bem.Radio>
    );
  }
}

export default Radio;
