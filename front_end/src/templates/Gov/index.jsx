import './styles.css';

import React, { useEffect, useState } from 'react';

import "@fortawesome/fontawesome-free/css/all.min.css";

import { BrHeader, BrFooter, BrMenu, BrBreadcrumbs, BrInput, BrButton } from "@govbr-ds/react-components";

import { Component } from 'react';

//class Gov extends Component {
export default function Gov () {

	const [ isCompact, setIsCompact ] = useState(false);

	const [searchTerm, setSearchTerm] = useState('');

	const [ documents, setDocuments ] = useState([]);

	useEffect(() => {

		const handleScroll = () => {
			const scrollY = window.scrollY;
			setIsCompact(scrollY > 40);
		};

		window.addEventListener('scroll', handleScroll);

		return () => window.removeEventListener('scroll', handleScroll);
	}, []);

	const handleSearch = () => {
		console.log('Buscando por:', searchTerm);
	};

	const headerMenu = [
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
	];

	const footerLinks = [
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
	];

	const atalhosRapidos = [
		{ label: 'Acessibilidade', link: '#' },
		{ label: 'Mapa do site', link: '#' },
		{ label: 'Ajuda', link: '#' }
	];

	const redesSociais = [
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
	];

	const menuLinks = [
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
	];

	const breadcrumbItems = [
		{ label: 'Início', href: '/', isHome: true },
		{ label: 'Composição', href: '#' },
		{ label: 'Saúde Indígena', active: true }
	  ];

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
				isWidescreen={false}
				density="medium"
				title="Ministério da Saúde"
				links={headerMenu}
				menuId="main-menu"
			/>

			<div className="container">
			<BrBreadcrumbs
				crumbs={breadcrumbItems}
			/></div>

			<BrMenu
				systemLogoUrl="/img/govbr.webp"
				systemName="Portal SESAI"
				closable={false} // Não está funcionando
				//socialNetworks={redesSociais}
				id="main-menu"
				title="Menu Principal"
				data={menuLinks}
			/>

			<div className="container my-5">

				<div className="search-container">
					<BrInput
						density="large"
						type="search"
						value={searchTerm}
						onChange={(e) => setSearchTerm(e.target.value)}
						placeholder="O que você procura?"
						button={<BrButton label="Buscar" icon="fas fa-search" onClick={handleSearch} />}
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
					<li><a href="#">Despacho</a></li>
					<li><a href="#">Documento de Formalização de Demanda</a></li>
					<li><a href="#">Documento técnico</a></li>
					<li><a href="#">Mapa de risco</a></li>
					<li><a href="#">Memorial</a></li>
					<li><a href="#">Ofício</a></li>
					<li><a href="#">Plano</a></li>
					<li><a href="#">Portaria</a></li>
					<li><a href="#">Projeto</a></li>
					<li><a href="#">Prontuário</a></li>
					<li><a href="#">Relatório Fotográfico</a></li>
					<li><a href="#">Termo de Contrato</a></li>
				</ul>
			</div>



			<BrFooter urlLogo="/img/govbr-negativa.png" links={footerLinks} socialNetworks={redesSociais} />

		</div>
	);
}

//export default Gov
