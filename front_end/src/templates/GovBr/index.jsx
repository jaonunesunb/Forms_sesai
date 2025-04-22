import './styles.css';

import React, { useEffect, useState } from 'react';

import "@fortawesome/fontawesome-free/css/all.min.css";

import { BrHeader, BrFooter, BrMenu, BrBreadcrumbs, BrInput, BrButton } from "@govbr-ds/react-components";

import { Component } from 'react';

import { loadDocuments } from '../../utils/load-documents';

class GovBr extends Component {
//export default function GovBr () {

	// const [ isCompact, setIsCompact ] = useState(false);
	//	const [searchTerm, setSearchTerm] = useState('');
	// const [ documents, setDocuments ] = useState([]);

	state = {
		isCompact: false,
		searchTerm: '',
		headerMenu: [],
		footerLinks: [],
		atalhosRapidos: [],
		redesSociais: [],
		documents: []
	}

	/*
	useEffect(() => {

		const handleScroll = () => {
			const scrollY = window.scrollY;
			setIsCompact(scrollY > 40);
		};

		window.addEventListener('scroll', handleScroll);

		return () => window.removeEventListener('scroll', handleScroll);
	}, []);
	*/

	// Função executada após os componentes serem montados
	componentDidMount() {

		/*

		const documentsResponse = fetch(`http://localhost:5000/get_subclasses?class=http://www.semanticweb.org/ontologias/OntoSesai/sesai_00000317`);

		const [ documents ] = await Promise.all([ documentsResponse ]);

		if (!response.ok) throw new Error('Erro ao buscar as classes.');
		const data = response.json();
			//this.setState({ documents: data.subclasses });
		*/

		this.loadDocuments();

	}

	loadDocuments = async() => {

		const documents = await loadDocuments();

		this.setState({
			documents: documents,
		});
	}

	setGovBr = () => {

		this.setState({
				headerMenu: [
					{
					label: 'Início',
					link: '#'
					},
					{
					label: 'Serviços',
					subItems: [
						{ label: 'Consulta', link: '#' },
						{ label: 'Agendamento', link: '#' }
					]
					},
					{
					label: 'Contato',
					link: '#'
					}
				],
				footerLinks: [
					{
					category: 'Institucional',
					items: [
						{ label: 'Sobre', link: '#' },
						{ label: 'Contato', link: '#' }
					]
					},
					{
					category: 'Serviços',
					items: [
						{ label: 'Portal', link: '#' },
						{ label: 'Atendimento', link: '#' }
					]
					}
				],
				atalhosRapidos: [
					{ label: 'Acessibilidade', link: '#' },
					{ label: 'Mapa do site', link: '#' },
					{ label: 'Ajuda', link: '#' }
				],
				redesSociais: [
					{
					icon: 'fa-linkedin fab ',
					link: 'https://github.com/govbr',
					name: 'GitHub'
					},
					{
					icon: 'fa-facebook fab ',
					link: 'https://facebook.com/govbr',
					name: 'Facebook'
					},
					{
					icon: 'fa-twitter fab ',
					link: 'https://twitter.com/govbr',
					name: 'Twitter'
					}
				],
				searchTerm: ''
			}
		);
	}



	handleChange = (e) => {
		const {value} = e.target;
		this.setState({ searchTerm: value });
	}


	render() {

		const { documents, headerMenu, footerLinks, atalhosRapidos, breadcrumbItems, menuLinks, redesSociais, searchTerm, isCompact } = this.state;

		return (

			<div className="template-base">

				<BrHeader
					urlLogo="/img/govbr.webp"
					showMenuButton={true}
					showSearchBar={true}
					showLoginButton={true}
					signature="Governo Federal"
					quickAccessLinks={atalhosRapidos}
					sticky={true}
					compact={isCompact}
					density="medium"
					title="Ministério da Saúde"
					links={headerMenu}
					menuId="main-menu"
				/>

				<div className="container"><BrBreadcrumbs crumbs={breadcrumbItems}/></div>

				<BrMenu
					systemLogoUrl="/img/govbr.webp"
					systemName="Portal SESAI"
					closable={false} // Não está funcionando
					//socialNetworks={redesSociais}
					id="main-menu"
					title="Menu Principal"
					data={menuLinks}
				/>

				<div className="container mb-5">

					<div className="search-container">
						<BrInput
							density="large"
							type="search"
							value={searchTerm}
							onChange={this.handleChange}
							placeholder="O que você procura?"
							button={<BrButton label="Buscar" icon="fas fa-search" onClick={this.handleChange} />}
						/>
					</div>

					<div className="row justify-content-center mb-5">
						<div className="col-md-6">
							<h4 className="text-center">Documentos consistentes, processos eficientes</h4>
							<p>O sistema de geração dinâmica de documentos da <strong>Secretaria de Saúde Indígena (SESAI)</strong> foi desenvolvido com base em ontologias para agilizar e padronizar a criação de documentos. Por meio de formulários adaptáveis a cada tipo documental, a ferramenta facilita a rastreabilidade, a padronização e a integração dos documentos com outras plataformas institucionais.</p>
						</div>
					</div>

					<div className="section-title-wrapper">
						<h2>Documentos disponíveis</h2>
					</div>

					<ul className="document-list">
						{documents.map(document => (
							<li key={document.uri}>
								<a href="#">{document.label}</a>
							</li>
						))}
					</ul>
				</div>

				<BrFooter urlLogo="/img/govbr-negativa.png" links={footerLinks} socialNetworks={redesSociais} />

			</div>
		);
	}
}

export default GovBr
