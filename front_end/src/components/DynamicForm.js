import React, { useState } from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';
import SelectField from './SelectField'; // Importa o componente SelectField
import InputField from './InputField';   // Importa o novo componente InputField

// Função para capitalizar a primeira letra
const capitalize = (text) => {
  return text.charAt(0).toUpperCase() + text.slice(1);
};

const DynamicForm = ({ formData }) => {
  const [formState, setFormState] = useState({});
  const [errors, setErrors] = useState({});
  const [dynamicFields, setDynamicFields] = useState([]);

  // Função de validação de tipos de dados
  const validateDataType = (value, dataType, restrictions) => {
    let error = '';
  
    if (value && dataType && dataType.length > 0) {
      switch (dataType[0]) {
        case 'http://www.w3.org/2001/XMLSchema#date':
          if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
            error = 'Data inválida. Use o formato AAAA-MM-DD.';
          }
          break;
        case 'http://www.w3.org/2001/XMLSchema#time':
          if (!/^\d{2}:\d{2}$/.test(value)) {
            error = 'Hora inválida. Use o formato HH:MM.';
          }
          break;
        case 'http://www.w3.org/2001/XMLSchema#integer':
          if (!/^\d+$/.test(value)) {
            error = 'Insira um número inteiro válido.';
          }
          break;
        case 'http://www.w3.org/2001/XMLSchema#float':
        case 'http://www.w3.org/2001/XMLSchema#decimal':
          if (isNaN(value)) {
            error = 'Insira um número decimal válido.';
          }
          break;
        case 'http://www.w3.org/2001/XMLSchema#boolean':
          if (!['true', 'false'].includes(value.toLowerCase())) {
            error = 'Selecione uma opção válida.';
          }
          break;
        default:
          break;
      }
  
      const maxLength = restrictions?.['xsd:maxLength'];
      if (maxLength && value.length > parseInt(maxLength)) {
        error = `O texto excede o comprimento máximo de ${maxLength} caracteres.`;
      }
    }
  
    return error;
  };

  // Função de validação de campos
  const validateField = (value, field) => {
    const { dataType, restrictions, cardinality } = field;
    let error = '';

    // Verificar se o campo é obrigatório
    const isRequired = cardinality && ['min 1', 'only', 'exactly 1', "some"].includes(cardinality);

    if (isRequired && !value) {
      error = 'Este campo é obrigatório.';
    } else {
      // Validar o tipo de dado do campo
      error = validateDataType(value, dataType, restrictions);
    }

    return error;
  };

  const handleChange = (key, value, field) => {
    setFormState((prevState) => ({
      ...prevState,
      [key]: value, // Atualiza corretamente o valor para a chave (campo)
    }));
  
    const error = validateField(value, field);
    setErrors((prevErrors) => ({
      ...prevErrors,
      [key]: error, // Atualiza os erros, se houver
    }));

    // Verifica se há subclasses e processa campos dinâmicos
    if (field.subclasses && field.subclasses.length > 0) {
      const selectedSubclass = field.subclasses.find((subclass) => subclass.uri === value);
      if (selectedSubclass) {
        const newField = {
            label: `Insira um(a) ${selectedSubclass.label || selectedSubclass.uri}`,  // Usar apenas o label ou a URI
            relatedClass: selectedSubclass.uri,
            dataType: ['http://www.w3.org/2001/XMLSchema#string'],
            property: selectedSubclass.label,
        };
           // Adiciona o campo dinâmico no estado, além de garantir que ele seja armazenado corretamente
    setDynamicFields((prevDynamicFields) => [...prevDynamicFields, newField]);
    setFormState((prevState) => ({
        ...prevState,
        [newField.relatedClass]: '', // Inicializa o valor do novo campo
    }));
} else {
    setDynamicFields([]);
}
}
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
  
    const newErrors = {};
    const validFormState = {}; // Novo objeto para armazenar os dados válidos
  
    formData.forEach((field) => {
      const key = generateKey(field);
      const value = formState[key];
  
      // Pular campos com status "em construção"
      if (field.status === 'em construção') {
        return;
      }
  
      // Verifica se o campo é obrigatório
      const isRequired = field.cardinality && ['min 1', 'only', 'exactly 1', "some"].includes(field.cardinality);
      
      // Validação do tipo de dado
      const dataTypeError = validateDataType(value, field.dataType, field.restrictions);
      if (dataTypeError) {
        newErrors[key] = dataTypeError;
      } else if (value) {
        // Inclui o campo no estado válido se tiver valor e o valor for válido
        validFormState[key] = value;
      }
  
      // Adiciona erro se o campo obrigatório estiver vazio
      if (isRequired && !value) {
        newErrors[key] = 'Este campo é obrigatório.';
      }
    });
  
    // Incluindo campos opcionais dinâmicos que foram adicionados
    dynamicFields.forEach((field) => {
      const key = generateKey(field);
      const value = formState[key];

      // Validação do tipo de dado
      const dataTypeError = validateDataType(value, field.dataType, field.restrictions);
      if (dataTypeError) {
        newErrors[key] = dataTypeError;
      } else if (value) {
        // Inclui o campo no estado válido se tiver valor e o valor for válido
        validFormState[key] = value;
      }
    });

    setErrors(newErrors);
  
    if (Object.keys(newErrors).length === 0) {
      try {
        const response = await fetch('http://127.0.0.1:5000/save_form_data', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(validFormState), // Envia todos os dados válidos
        });
  
        if (response.ok) {
          console.log('Formulário enviado com sucesso!');
          downloadJSON(validFormState, 'form_data.json');
        } else {
          console.error('Erro ao enviar o formulário');
        }
      } catch (error) {
        console.error('Erro na requisição:', error);
      }
    } else {
      console.log('Erros no formulário:', newErrors);
    }
  };

  const generateKey = (field) => {
    return `${field.relatedClass}-${field.property}`;
  };

  const renderField = (field, index) => {
    const { label, dataType, restrictions, cardinality, relatedClass, status, subclasses } = field;
    const key = generateKey(field);

    if (status === 'em construção') {
      return null;
    }

    const isRequired = cardinality && ['min 1', 'only', 'exactly 1', 'some'].includes(cardinality);

    if (subclasses && subclasses.length > 0) {
      return (
        <SelectField
          key={index}
          field={field}
          value={formState[key]}
          handleChange={handleChange}
          errors={errors}
          isRequired={isRequired}
        />
      );
    }

    return (
      <InputField
        key={index}
        field={field}
        value={formState[key]}
        handleChange={handleChange}
        errors={errors}
        isRequired={isRequired}
      />
    );
  };

  const renderFields = () => {
    if (!formData || formData.length === 0) {
      return <div className="alert alert-info">Nenhum campo disponível para este formulário.</div>;
    }
    return formData.map((field, index) => renderField(field, index));
  };

  return (
    <form className="form-container" onSubmit={handleSubmit}>
      {renderFields()}
      {dynamicFields.length > 0 && dynamicFields.map((field, index) => renderField(field, index))}
      <button type="submit" className="btn btn-primary mt-4">Enviar</button>
    </form>
  );
};

const downloadJSON = (data, filename) => {
  const jsonStr = JSON.stringify(data, null, 2); // Converter o JSON em string formatada
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

export default DynamicForm;
