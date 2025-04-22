import React from 'react';

const SelectField = ({ field, value, handleChange, errors, isRequired }) => {
  const { label, relatedClass, subclasses } = field;
  const key = `${relatedClass}-${field.property}`;

  return (
    <div className="br-input  mb-3">
      <label>{capitalize(label)}</label>
      <select
        id={key}
        className={`form-control ${errors[key] ? 'is-invalid' : ''}`}
        value={value || ''}
        onChange={(e) => handleChange(key, e.target.value, field)}
        required={isRequired}
      >
        <option value="">Selecione</option>
        {subclasses.map((subclass) => (
          <option key={subclass.uri} value={subclass.uri}>
            {subclass.label || subclass.uri}
          </option>
        ))}
      </select>
      {errors[key] && <div className="invalid-feedback">{errors[key]}</div>}
    </div>
  );
};

const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);

export default SelectField;
