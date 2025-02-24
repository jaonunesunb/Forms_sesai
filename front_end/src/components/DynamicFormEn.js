import React, { useState } from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';

const DynamicFormEn = ({ formData }) => {
  const [formState, setFormState] = useState({});
  const [errors, setErrors] = useState({});

  const handleChange = (key, value) => {
    setFormState(prevState => ({
      ...prevState,
      [key]: value,
    }));

    const field = formData.find(f => generateKey(f) === key);
    if (field) {
      const error = validateField(value, field);
      setErrors(prevErrors => ({
        ...prevErrors,
        [key]: error,
      }));
    }
  };

  const validateField = (value, field) => {
    const { dataType, restrictions, cardinality } = field;
    let error = '';

    const isRequired = ['min 1', 'only', 'exactly 1', 'some'].includes(cardinality);
    if (isRequired && !value) {
      return 'This field is required.';
    }

    if (value) {
      switch (dataType[0]) {
        case 'http://www.w3.org/2001/XMLSchema#date':
          if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
            error = 'Invalid date format. Use YYYY-MM-DD.';
          }
          break;
        case 'http://www.w3.org/2001/XMLSchema#time':
          if (!/^\d{2}:\d{2}$/.test(value)) {
            error = 'Invalid time format. Use HH:MM.';
          }
          break;
        case 'http://www.w3.org/2001/XMLSchema#integer':
          if (!/^\d+$/.test(value)) {
            error = 'Enter a valid integer.';
          }
          break;
        case 'http://www.w3.org/2001/XMLSchema#float':
        case 'http://www.w3.org/2001/XMLSchema#decimal':
          if (isNaN(value)) {
            error = 'Enter a valid decimal number.';
          }
          break;
        case 'http://www.w3.org/2001/XMLSchema#boolean':
          if (!['true', 'false'].includes(value.toLowerCase())) {
            error = 'Select a valid option.';
          }
          break;
        default:
          break;
      }

      const maxLength = restrictions?.['xsd:maxLength'];
      if (maxLength && value.length > parseInt(maxLength)) {
        error = `Text exceeds maximum length of ${maxLength} characters.`;
      }
    }

    return error;
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const newErrors = {};
    formData.forEach(field => {
      const key = generateKey(field);
      const value = formState[key];
      const error = validateField(value, field);
      if (error) {
        newErrors[key] = error;
      }
    });

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      // Save the form data as JSON file
      const jsonData = JSON.stringify(formState);
      const blob = new Blob([jsonData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'formData.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      console.log('Form is valid and saved as JSON!', formState);
    } else {
      console.log('Form errors:', newErrors);
    }
  };

  const generateKey = (field) => {
    return `${field.relatedClass}-${field.property}`;
  };

  // Render dropdowns or inputs depending on subclasses
  const renderField = (field, index) => {
    const { property, label, dataType, restrictions, cardinality, relatedClass, status, subclasses } = field;
    const key = generateKey(field);

    // Check if dataType is defined. If not, don't render the field.
    if (!dataType || dataType.length === 0) {
      return null;
    }

    if (status === 'in construction') {
      return (
        <div key={index} className="form-group">
          <label>{`${label} (${relatedClass})`}</label>
          <div className="alert alert-warning">
            This field is under construction and cannot be filled at the moment.
          </div>
        </div>
      );
    }

    if (subclasses && subclasses.length > 0) {
      return (
        <div key={index} className="form-group">
          <label htmlFor={key}>{`${label} (${relatedClass})`}</label>
          <select
            id={key}
            className={`form-control ${errors[key] ? 'is-invalid' : ''}`}
            value={formState[key] || ''}
            onChange={(e) => handleChange(key, e.target.value)}
          >
            <option value="">Select</option>
            {subclasses.map(subclass => (
              <option key={subclass.uri} value={subclass.uri}>
                {subclass.label}
              </option>
            ))}
          </select>
          {errors[key] && <div className="invalid-feedback">{errors[key]}</div>}
        </div>
      );
    }

    let inputType = 'text';
    if (Array.isArray(dataType) && dataType.includes('http://www.w3.org/2001/XMLSchema#date')) inputType = 'date';
    else if (Array.isArray(dataType) && dataType.includes('http://www.w3.org/2001/XMLSchema#time')) inputType = 'time';
    else if (Array.isArray(dataType) && dataType.includes('http://www.w3.org/2001/XMLSchema#integer')) inputType = 'number';
    else if (Array.isArray(dataType) && (dataType.includes('http://www.w3.org/2001/XMLSchema#float') || dataType.includes('http://www.w3.org/2001/XMLSchema#decimal'))) inputType = 'number';
    else if (Array.isArray(dataType) && dataType.includes('http://www.w3.org/2001/XMLSchema#boolean')) inputType = 'select';

    const isRequired = ['min 1', 'only', 'exactly 1'].includes(cardinality);
    const maxLength = restrictions?.['xsd:maxLength'] ? parseInt(restrictions['xsd:maxLength']) : undefined;

    return (
      <div key={index} className="form-group">
        <label htmlFor={key}>{`${label} (${relatedClass})`} {isRequired && <span className="text-danger">*</span>}</label>
        {inputType === 'select' ? (
          <select
            id={key}
            className={`form-control ${errors[key] ? 'is-invalid' : ''}`}
            value={formState[key] || ''}
            onChange={(e) => handleChange(key, e.target.value)}
            required={isRequired}
          >
            <option value="">Select</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        ) : (
          <input
            id={key}
            type={inputType}
            className={`form-control ${errors[key] ? 'is-invalid' : ''}`}
            value={formState[key] || ''}
            onChange={(e) => handleChange(key, e.target.value)}
            required={isRequired}
            maxLength={maxLength}
            placeholder={maxLength ? `Maximum of ${maxLength} characters` : ''}
            step={inputType === 'number' && (dataType.includes('float') || dataType.includes('decimal')) ? 'any' : undefined}
          />
        )}
        {errors[key] && <div className="invalid-feedback">{errors[key]}</div>}
      </div>
    );
  };

  const renderFields = () => {
    if (!formData || formData.length === 0) {
      return <div className="alert alert-info">No fields available for this form.</div>;
    }
    return formData.map((field, index) => renderField(field, index));
  };

  return (
    <form className="form-container" onSubmit={handleSubmit}>
      {renderFields()}
      <button type="submit" className="btn btn-primary mt-4">Submit</button>
    </form>
  );
};

export default DynamicFormEn;
