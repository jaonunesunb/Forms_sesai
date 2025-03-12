import React, { useEffect, useState } from 'react';
import DynamicForm from './components/DynamicForm'; // Formulário em português
import DynamicFormEn from './components/DynamicFormEn'; // Formulário em inglês
import Header from './components/Header';
import Footer from './components/Footer';
import 'bootstrap/dist/css/bootstrap.min.css';

function App() {
  const [classHierarchy, setClassHierarchy] = useState([
    {
      label: 'documento',
      uri: 'http://www.semanticweb.org/ontologias/OntoSesai/sesai_00000317',
      subclasses: [],
      loading: false,
      selectedSubclass: null,
    },
  ]);

  const [previousActivityLabel, setPreviousActivityLabel] = useState(''); // Estado para armazenar o label da subclasse selecionada
  const [formData, setFormData] = useState(null);
  const [formLoading, setFormLoading] = useState(false);
  const [error, setError] = useState(null);
  const [language, setLanguage] = useState('pt'); // Estado que controla o idioma

  // Função para buscar o idioma do backend
  const fetchLanguage = async () => {
    try {
      const response = await fetch(`http://localhost:5000/get_language`);
      if (!response.ok) throw new Error('Erro ao buscar idioma');
      const data = await response.json();
      setLanguage(data.language); // Recebe o idioma do backend
    } catch (err) {
      console.error(err);
      setError(err.message);
    }
  };

  // Função para alterar o idioma
  const changeLanguage = async (newLanguage) => {
    try {
      const response = await fetch(`http://localhost:5000/set_language`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: newLanguage }),
      });
      if (!response.ok) throw new Error('Erro ao alterar idioma');
      setLanguage(newLanguage);
      fetchSubclasses(classHierarchy[0].uri, 0); // Atualizar as subclasses após a troca de idioma
    } catch (err) {
      console.error(err);
      setError(err.message);
    }
  };

  // Função para buscar subclasses
  const fetchSubclasses = async (uri, levelIndex) => {
    try {
      setError(null);
      const updatedHierarchy = [...classHierarchy];

      if (!updatedHierarchy[levelIndex]) {
        updatedHierarchy[levelIndex] = {
          label: '',
          uri: '',
          subclasses: [],
          loading: false,
          selectedSubclass: null,
        };
      }

      updatedHierarchy[levelIndex].loading = true;
      setClassHierarchy(updatedHierarchy);

      const response = await fetch(`http://localhost:5000/get_subclasses?class=${encodeURIComponent(uri)}`);
      if (!response.ok) throw new Error('Erro ao carregar subclasses');
      const data = await response.json();

      if (data.subclasses.length > 0) {
        updatedHierarchy[levelIndex].subclasses = data.subclasses;
        updatedHierarchy[levelIndex].loading = false;
        updatedHierarchy[levelIndex].label = data.label;

        setClassHierarchy(updatedHierarchy.slice(0, levelIndex + 1));
        setFormData(null);
      } else {
        fetchFormData(uri);
      }
    } catch (err) {
      console.error(err);
      setError(err.message);
    }
  };

  // Função para lidar com a seleção de uma subclasse
  const handleSubclassSelect = (uri, levelIndex) => {
    const updatedHierarchy = [...classHierarchy];
    updatedHierarchy[levelIndex].selectedSubclass = uri;

    // Quando o usuário seleciona a primeira subclasse, armazenar o label da subclasse
    if (levelIndex === 0) {
      const selectedSubclass = updatedHierarchy[levelIndex].subclasses.find(subclass => subclass.uri === uri);
      if (selectedSubclass) {
        setPreviousActivityLabel(selectedSubclass.label); // Armazena o label da subclasse selecionada
      }
      fetchSubclasses(uri, levelIndex + 1);
    } else {
      fetchFormData(uri);
    }

    setClassHierarchy(updatedHierarchy);
  };

  // Função para buscar dados do formulário
  const fetchFormData = async (uri) => {
    try {
      setFormLoading(true);
      setError(null);
      const response = await fetch(`http://localhost:5000/get_class_details?class=${encodeURIComponent(uri)}`);
      if (!response.ok) throw new Error('Erro ao carregar dados do formulário');
      const data = await response.json();
      setFormData(data);
      setFormLoading(false);
    } catch (err) {
      console.error(err);
      setError(err.message);
      setFormLoading(false);
    }
  };

  // Carregar as subclasses iniciais e o idioma na montagem do componente
  useEffect(() => {
    fetchSubclasses(classHierarchy[0].uri, 0);
    fetchLanguage(); // Busca o idioma ao iniciar o aplicativo
  }, []);

  return (
    <div className="App">
      <Header />
      <main className="container mt-4">
        <div className="card card-custom">
          <div className="card-body">
            <h2 className="form-title">
              {language === 'pt' ? 'Formulário Dinâmico de Cadastro' : 'Dynamic Registration Form'}
            </h2>

            {error && (
              <div className="alert alert-danger" role="alert">
                {error}
              </div>
            )}

            <div className="mb-4 d-flex justify-content-end">
              <button className="btn btn-secondary" onClick={() => changeLanguage(language === 'pt' ? 'en' : 'pt')}>
                {language === 'pt' ? 'Switch to English' : 'Mudar para Português'}
              </button>
            </div>

            <div className="mb-4">
              {classHierarchy.map((level, index) => (
                <div key={index} className="form-group mb-3">
                  <label>
                    {index === 0
                      ? language === 'pt' ? 'Selecione um tipo de documento' : 'Select a type of document'
                      : language === 'pt' ? `Selecione um(a) ${previousActivityLabel}` : `Select a(n) ${previousActivityLabel}`}
                  </label>
                  {level.loading ? (
                    <div>{language === 'pt' ? 'Carregando...' : 'Loading...'}</div>
                  ) : (
                    <select
                      className="form-control"
                      value={level.selectedSubclass || ''}
                      onChange={(e) => handleSubclassSelect(e.target.value, index)}
                    >
                      <option value="">{language === 'pt' ? 'Selecione' : 'Select'}</option>
                      {level.subclasses.map((subclass) => (
                        <option key={subclass.uri} value={subclass.uri}>
                          {subclass.label}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              ))}
            </div>

            {formLoading && <div>{language === 'pt' ? 'Carregando formulário...' : 'Loading form...'}</div>}
            {formData && !formLoading && (
              language === 'pt'
                ? <DynamicForm formData={formData} />
                : <DynamicFormEn formData={formData} />
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default App;
