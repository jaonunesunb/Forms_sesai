import React from 'react';

const InputField = ({ field, value, handleChange, errors, isRequired }) => {
  const { label, relatedClass, dataType, restrictions } = field;
  const key = `${relatedClass}-${field.property}`;

  let inputType = 'text';
  if (dataType && dataType.includes('http://www.w3.org/2001/XMLSchema#date')) inputType = 'date';
  else if (dataType && dataType.includes('http://www.w3.org/2001/XMLSchema#time')) inputType = 'time';
  else if (dataType && dataType.includes('http://www.w3.org/2001/XMLSchema#integer')) inputType = 'number';
  else if (dataType && (dataType.includes('http://www.w3.org/2001/XMLSchema#float') || dataType.includes('http://www.w3.org/2001/XMLSchema#decimal'))) inputType = 'number';
  else if (dataType && dataType.includes('http://www.w3.org/2001/XMLSchema#boolean')) inputType = 'select';

  const maxLength = restrictions?.['xsd:maxLength'] ? parseInt(restrictions['xsd:maxLength']) : undefined;

  return (
    <div className="form-group">
      <label htmlFor={key}>
        {capitalize(label)} ({capitalize(relatedClass)}) 
        {isRequired ? <span className="text-danger"> *</span> : <span className="text-muted"> (Opcional)</span>}
      </label>

      {inputType === 'select' ? (
        <select
          id={key}
          className={`form-control ${errors[key] ? 'is-invalid' : ''}`}
          value={value || ''}
          onChange={(e) => handleChange(key, e.target.value, field)}
          required={isRequired}
        >
          <option value="">Selecione</option>
          <option value="true">Sim</option>
          <option value="false">Não</option>
        </select>
      ) : maxLength && maxLength > 200 ? (
        <textarea
          id={key}
          className={`form-control ${errors[key] ? 'is-invalid' : ''}`}
          value={value || ''}
          onChange={(e) => handleChange(key, e.target.value, field)}
          required={isRequired}
          maxLength={maxLength}
          placeholder={`Máximo de ${maxLength} caracteres`}
        />
      ) : (
        <input
          id={key}
          type={inputType}
          className={`form-control ${errors[key] ? 'is-invalid' : ''}`}
          value={value || ''}
          onChange={(e) => handleChange(key, e.target.value, field)}
          required={isRequired}
          maxLength={maxLength}
          placeholder={maxLength ? `Máximo de ${maxLength} caracteres` : ''}
          step={inputType === 'number' ? 'any' : undefined}
        />
      )}

      {errors[key] && <div className="invalid-feedback">{errors[key]}</div>}
    </div>
  );
};

const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);

export default InputField;
