(() => {
  "use strict";

  const STORAGE_KEY = "devlink.language";
  const DEFAULT_LANGUAGE = "es";
  const SUPPORTED_LANGUAGES = ["es", "en", "pt-BR"];

  const translations = {
    en: {
      "meta.title": "devLink | Data migration and custom automation",
      "meta.description": "Data migration, implementation support, process automation, custom web applications and chatbots, hosted in our cloud or your infrastructure.",
      "nav.openMenu": "Open menu",
      "nav.closeMenu": "Close menu",
      "nav.home": "Home",
      "nav.services": "Services",
      "nav.suite": "Suite Lite",
      "nav.solutions": "Solutions",
      "nav.method": "Methodology",
      "nav.portal": "Client Portal",
      "nav.language": "Language",
      "nav.contact": "Schedule a consultation",
      "hero.eyebrow": "Migration, automation and development at your pace",
      "hero.title": "We turn data and processes into value for your business",
      "hero.body": "We support your team throughout every implementation. We migrate critical data without stopping operations, automate tasks with RPA and Arduino hardware, and build web applications and chatbots that connect with your systems. Host them in our managed cloud or on your own servers.",
      "hero.primary": "Plan a discovery session",
      "hero.secondary": "Explore our solutions",
      "hero.bullet1": "Reliable migrations from D365, SAP and TMW-WMS",
      "hero.bullet2": "Agile automation with RPA and Arduino control",
      "hero.bullet3": "Web applications and chatbots ready to grow with you",
      "hero.cardTitle": "What we achieve together",
      "hero.card1": "data migrations and synchronizations without downtime",
      "hero.card2": "fewer manual tasks thanks to RPA workflows",
      "hero.card3": "corporate websites and chatbots running in production",
      "hero.badgeTitle": "devLink infrastructure",
      "hero.badgeBody": "We host your solutions in our cloud or yours, with ongoing security, monitoring and support.",
      "proof.title": "Clear results for your implementations",
      "proof.body": "We reduce risk, speed up adoption and prepare your teams to operate from day one.",
      "proof.stat1": "Data integrity verified in every migration and synchronization we deliver.",
      "proof.stat2Value": "3 weeks",
      "proof.stat2": "Average time to launch RPA automations that reduce your team's workload.",
      "proof.stat3": "Monitoring and support for solutions hosted in the devLink cloud.",
      "trust.eyebrow": "Proven experience",
      "trust.title": "Companies that have trusted us",
      "trust.body": "We support teams and businesses that need to organize processes, connect systems and turn an idea into a tool that works.",
      "trust.ribbonLabel": "Companies that have trusted devLink",
      "trust.visitKepedimos": "Visit the KePedimos website",
      "trust.visitAdn": "Visit the ADN Soft website",
      "trust.visitOficios": "Visit the Oficios Market website",
      "trust.visitCamping": "Visit the Camping ACA Luján website",
      "trust.visitSecure": "Visit the SecureApprove website",
      "trust.visitDistromaxi": "Visit the Distromaxi website",
      "trust.visitMyc": "Visit the MyC Digitalización website",
      "services.title": "Services that make technology easier",
      "services.body": "We join your team so technology stops being a problem and becomes an everyday advantage.",
      "services.data.title": "Migration and reliable data",
      "services.data.body": "We plan and carry out migrations from D365, SAP, TMW-WMS and other platforms without stopping operations.",
      "services.data.bullet1": "Source mapping and data cleanup",
      "services.data.bullet2": "Integrity testing and contingency planning",
      "services.data.bullet3": "Supported go-live through stabilization",
      "services.implementation.title": "Implementation support",
      "services.implementation.body": "We take part in your key projects as an extension of your team, with coordination, workshops and practical support that drive adoption.",
      "services.implementation.bullet1": "ERP, CRM and WMS implementations",
      "services.implementation.bullet2": "RMA processes and traceable logistics",
      "services.implementation.bullet3": "Training with easy-to-follow material",
      "services.automation.title": "Custom automation",
      "services.automation.body": "We build RPA workflows and Arduino solutions that remove repetitive tasks and connect your data.",
      "services.automation.bullet1": "Bots that connect systems and spreadsheets",
      "services.automation.bullet2": "Sensor reading and remote control",
      "services.automation.bullet3": "Real-time alerts for your team",
      "services.digital.title": "Digital experiences",
      "services.digital.body": "We build corporate websites, applications and chatbots connected to WhatsApp and AI models.",
      "services.digital.bullet1": "Easy-to-use portals and internal tools",
      "services.digital.bullet2": "AI chatbots and the WhatsApp Business API",
      "services.digital.bullet3": "Hosting in our cloud or on your servers",
      "services.web.title": "Website development",
      "services.web.body": "We create modern corporate websites that present your business clearly and work well on every device.",
      "services.web.bullet1": "Responsive design for desktop and mobile",
      "services.web.bullet2": "Clear content that is easy to navigate",
      "services.web.bullet3": "Publishing and support for continued growth",
      "services.ecommerce.title": "E-commerce for small and medium businesses",
      "services.ecommerce.body": "We build online stores that help small and medium businesses sell and manage their operation.",
      "services.ecommerce.bullet1": "Catalog, cart and order management",
      "services.ecommerce.bullet2": "Payment method integrations",
      "services.ecommerce.bullet3": "A simple, responsive shopping experience",
      "services.android.title": "Android application development",
      "services.android.body": "We build Android applications aligned with your processes, users and existing business systems.",
      "services.android.bullet1": "Interfaces for phones and tablets",
      "services.android.bullet2": "Integration with existing APIs and services",
      "services.android.bullet3": "Ongoing maintenance and improvement",
      "services.custom.title": "Custom web applications",
      "services.custom.body": "We turn specific business processes into secure, clear web tools that are accessible from anywhere.",
      "services.custom.bullet1": "Portals, dashboards and internal workflows",
      "services.custom.bullet2": "Integrations with your current platforms",
      "services.custom.bullet3": "Solutions ready to support your growth",
      "suite.eyebrow": "devLink products",
      "suite.title": "Suite Lite: a solid foundation to operate and grow",
      "suite.body": "Six products that can work together or be added as your business needs them. We adapt them to your current processes and systems.",
      "suite.cta": "Request a demo",
      "suite.pos": "A reliable point of sale that speeds up service, keeps every transaction under control and integrates with SAP.",
      "suite.core": "The POS administration center for managing products, prices, users and data.",
      "suite.logistic": "Transportation and warehouse management for organizing inventory, movements, deliveries and routes.",
      "suite.ecommerce": "An online store connected to your products, prices, orders and availability, without duplicated work.",
      "suite.flow": "The bridge that exchanges information between SAP, Suite Lite and your company's other systems.",
      "suite.crm": "Simple tracking of customers, contacts and opportunities to organize sales activity.",
      "solutions.title": "How we connect your processes end to end",
      "solutions.body": "We bring technology and people together so every area of the business works with the same information.",
      "solutions.data.title": "Data ready for decisions",
      "solutions.data.body": "We centralize information from your systems and turn it into clear dashboards and reports you can act on.",
      "solutions.data.bullet1": "Unified data models",
      "solutions.data.bullet2": "Easy-to-understand business reports",
      "solutions.data.bullet3": "Automatic alerts when something changes",
      "solutions.processes.title": "Processes that flow",
      "solutions.processes.body": "We automate tasks with RPA and build Arduino routines that give your teams more time.",
      "solutions.processes.bullet1": "Workflows connecting ERP, CRM and WMS",
      "solutions.processes.bullet2": "One-click inventory and RMA control",
      "solutions.processes.bullet3": "Proactive issue tracking",
      "solutions.infrastructure.title": "Flexible infrastructure",
      "solutions.infrastructure.body": "We deploy in our managed cloud or on your servers, always with continuous monitoring and support.",
      "solutions.infrastructure.bullet1": "Controlled deployments and operations",
      "solutions.infrastructure.bullet2": "Backups and recovery plans",
      "solutions.infrastructure.bullet3": "Integration with your security policies",
      "method.title": "A method centered on your team",
      "method.body": "We work together so every step is clear, measurable and predictable.",
      "method.diagnosis.title": "Listen and diagnose",
      "method.diagnosis.body": "We learn how you operate, review data sources and identify opportunities to improve.",
      "method.plan.title": "A shared plan",
      "method.plan.body": "We define milestones, owners and success measures the whole team can follow.",
      "method.implementation.title": "Guided implementation",
      "method.implementation.body": "We carry out migrations, automations and development with testing and daily support.",
      "method.improvement.title": "Continuous improvement",
      "method.improvement.body": "We monitor results, make adjustments and transfer knowledge so your team can work independently.",
      "cta.title": "Ready to move your project forward with confidence?",
      "cta.body": "Let's meet and build a clear plan for your migration, automation or next development project.",
      "cta.button": "Book a call",
      "contact.eyebrow": "Let's work together",
      "contact.title": "Tell us what you need to solve",
      "contact.body": "Leave your details and a consultant will contact you within 24 hours with practical next steps.",
      "contact.bullet1": "Free kickoff to understand your context",
      "contact.bullet2": "Confidentiality and respect for your data",
      "contact.bullet3": "A multidisciplinary team at your service",
      "contact.nameLabel": "Full name",
      "contact.namePlaceholder": "Your name",
      "contact.emailLabel": "Email address",
      "contact.emailPlaceholder": "name@company.com",
      "contact.companyLabel": "Company",
      "contact.companyPlaceholder": "Your company name",
      "contact.interestTitle": "Interested in Suite Lite?",
      "contact.interestBody": "Tell us which product you would like to explore in your message.",
      "contact.projectLabel": "What do you need to solve?",
      "contact.projectPlaceholder": "Explore Suite Lite, migrate data, automate processes...",
      "contact.newsletter": "I want to receive ideas and news from devLink.",
      "contact.submit": "Request my assessment",
      "contact.note": "By submitting, you accept our privacy policy and responsible use of your data.",
      "footer.tagline": "We host and develop technology solutions centered on people.",
      "footer.contact": "Contact",
      "footer.follow": "Follow us",
      "footer.legal": "Legal",
      "footer.privacy": "Privacy Policy",
      "footer.terms": "Terms of Service",
      "footer.copyright": "devLink. All rights reserved."
    },
    "pt-BR": {
      "meta.title": "devLink | Migração de dados e automação sob medida",
      "meta.description": "Migração de dados, apoio a implantações, automação de processos, aplicações web sob medida e chatbots, em nossa nuvem ou na sua infraestrutura.",
      "nav.openMenu": "Abrir menu",
      "nav.closeMenu": "Fechar menu",
      "nav.home": "Início",
      "nav.services": "Serviços",
      "nav.suite": "Suite Lite",
      "nav.solutions": "Soluções",
      "nav.method": "Metodologia",
      "nav.portal": "Portal do Cliente",
      "nav.language": "Idioma",
      "nav.contact": "Agendar uma conversa",
      "hero.eyebrow": "Migração, automação e desenvolvimento no seu ritmo",
      "hero.title": "Transformamos dados e processos em valor para o seu negócio",
      "hero.body": "Acompanhamos sua equipe em cada implantação. Migramos dados críticos sem interromper a operação, automatizamos tarefas com RPA e hardware Arduino e desenvolvemos aplicações web e chatbots integrados aos seus sistemas. Você pode hospedá-los em nossa nuvem gerenciada ou nos seus próprios servidores.",
      "hero.primary": "Planejar uma reunião de descoberta",
      "hero.secondary": "Conhecer nossas soluções",
      "hero.bullet1": "Migrações confiáveis a partir de D365, SAP e TMW-WMS",
      "hero.bullet2": "Automações ágeis com RPA e controle Arduino",
      "hero.bullet3": "Aplicações web e chatbots prontos para crescer com você",
      "hero.cardTitle": "O que alcançamos juntos",
      "hero.card1": "migrações e sincronizações de dados sem interrupções",
      "hero.card2": "menos tarefas manuais graças aos fluxos de RPA",
      "hero.card3": "sites corporativos e chatbots ativos em produção",
      "hero.badgeTitle": "Infraestrutura devLink",
      "hero.badgeBody": "Hospedamos suas soluções em nossa nuvem ou na sua, com segurança, monitoramento e suporte contínuo.",
      "proof.title": "Resultados claros para suas implantações",
      "proof.body": "Reduzimos riscos, aceleramos a adoção e preparamos suas equipes para operar desde o primeiro dia.",
      "proof.stat1": "Integridade dos dados verificada em cada migração e sincronização entregue.",
      "proof.stat2Value": "3 semanas",
      "proof.stat2": "Tempo médio para lançar automações de RPA que aliviam a carga da sua equipe.",
      "proof.stat3": "Monitoramento e suporte para soluções hospedadas na nuvem devLink.",
      "trust.eyebrow": "Experiência comprovada",
      "trust.title": "Empresas que confiaram em nós",
      "trust.body": "Apoiamos equipes e empresas que precisavam organizar processos, conectar sistemas e transformar uma ideia em uma ferramenta que funciona.",
      "trust.ribbonLabel": "Empresas que confiaram na devLink",
      "trust.visitKepedimos": "Visitar o site da KePedimos",
      "trust.visitAdn": "Visitar o site da ADN Soft",
      "trust.visitOficios": "Visitar o site da Oficios Market",
      "trust.visitCamping": "Visitar o site do Camping ACA Luján",
      "trust.visitSecure": "Visitar o site da SecureApprove",
      "trust.visitDistromaxi": "Visitar o site da Distromaxi",
      "trust.visitMyc": "Visitar o site da MyC Digitalización",
      "services.title": "Serviços que simplificam a tecnologia",
      "services.body": "Entramos para a sua equipe para que a tecnologia deixe de ser um problema e se torne uma vantagem no dia a dia.",
      "services.data.title": "Migração e dados confiáveis",
      "services.data.body": "Planejamos e executamos migrações a partir de D365, SAP, TMW-WMS e outras plataformas sem interromper a operação.",
      "services.data.bullet1": "Mapeamento de origens e limpeza de dados",
      "services.data.bullet2": "Testes de integridade e plano de contingência",
      "services.data.bullet3": "Entrada em produção acompanhada até a estabilização",
      "services.implementation.title": "Apoio a implantações",
      "services.implementation.body": "Participamos dos seus projetos mais importantes como uma extensão da equipe, com coordenação, workshops e suporte prático para garantir a adoção.",
      "services.implementation.bullet1": "Implantações de ERP, CRM e WMS",
      "services.implementation.bullet2": "Processos de RMA e logística rastreável",
      "services.implementation.bullet3": "Treinamento com material fácil de acompanhar",
      "services.automation.title": "Automação sob medida",
      "services.automation.body": "Criamos fluxos de RPA e soluções Arduino que eliminam tarefas repetitivas e conectam seus dados.",
      "services.automation.bullet1": "Bots que integram sistemas e planilhas",
      "services.automation.bullet2": "Leitura de sensores e controle remoto",
      "services.automation.bullet3": "Alertas em tempo real para sua equipe",
      "services.digital.title": "Experiências digitais",
      "services.digital.body": "Desenvolvemos sites corporativos, aplicações e chatbots integrados ao WhatsApp e a modelos de IA.",
      "services.digital.bullet1": "Portais e ferramentas internas fáceis de usar",
      "services.digital.bullet2": "Chatbots com IA e API do WhatsApp Business",
      "services.digital.bullet3": "Hospedagem em nossa nuvem ou nos seus servidores",
      "services.web.title": "Desenvolvimento de sites",
      "services.web.body": "Criamos sites corporativos modernos que apresentam seu negócio com clareza e funcionam bem em qualquer dispositivo.",
      "services.web.bullet1": "Design responsivo para computador e celular",
      "services.web.bullet2": "Conteúdo claro e fácil de navegar",
      "services.web.bullet3": "Publicação e suporte para continuar crescendo",
      "services.ecommerce.title": "E-commerce para pequenas e médias empresas",
      "services.ecommerce.body": "Desenvolvemos lojas virtuais para que pequenas e médias empresas possam vender e administrar sua operação.",
      "services.ecommerce.bullet1": "Catálogo, carrinho e gestão de pedidos",
      "services.ecommerce.bullet2": "Integração com meios de pagamento",
      "services.ecommerce.bullet3": "Experiência de compra simples e responsiva",
      "services.android.title": "Desenvolvimento de aplicações Android",
      "services.android.body": "Criamos aplicações Android alinhadas aos seus processos, usuários e sistemas atuais.",
      "services.android.bullet1": "Interfaces adaptadas para celulares e tablets",
      "services.android.bullet2": "Integração com APIs e serviços existentes",
      "services.android.bullet3": "Manutenção e evolução contínua",
      "services.custom.title": "Aplicações web sob medida",
      "services.custom.body": "Transformamos processos específicos do seu negócio em ferramentas web seguras, claras e acessíveis de qualquer lugar.",
      "services.custom.bullet1": "Portais, painéis e fluxos internos",
      "services.custom.bullet2": "Integrações com suas plataformas atuais",
      "services.custom.bullet3": "Soluções preparadas para acompanhar o crescimento",
      "suite.eyebrow": "Produtos devLink",
      "suite.title": "Suite Lite: uma base sólida para operar e crescer",
      "suite.body": "Seis produtos que podem trabalhar juntos ou ser incorporados conforme as necessidades da sua empresa. Adaptamos cada um aos seus processos e sistemas atuais.",
      "suite.cta": "Solicitar uma demonstração",
      "suite.pos": "Um ponto de venda confiável para agilizar o atendimento, controlar cada operação e trabalhar integrado ao SAP.",
      "suite.core": "O centro de administração do POS para manter produtos, preços, usuários e dados sob controle.",
      "suite.logistic": "Gestão de transporte e armazéns para organizar estoque, movimentações, entregas e rotas.",
      "suite.ecommerce": "Uma loja virtual conectada aos seus produtos, preços, pedidos e disponibilidade, sem duplicar tarefas.",
      "suite.flow": "A ponte que permite trocar informações entre SAP, Suite Lite e os demais sistemas da sua empresa.",
      "suite.crm": "Acompanhamento simples de clientes, contatos e oportunidades para organizar a atividade comercial.",
      "solutions.title": "Como conectamos seus processos de ponta a ponta",
      "solutions.body": "Integramos tecnologia e pessoas para que todas as áreas do negócio trabalhem com as mesmas informações.",
      "solutions.data.title": "Dados prontos para decisões",
      "solutions.data.body": "Centralizamos as informações dos seus sistemas e as transformamos em painéis e relatórios claros para agir.",
      "solutions.data.bullet1": "Modelos de dados unificados",
      "solutions.data.bullet2": "Relatórios de negócio fáceis de entender",
      "solutions.data.bullet3": "Alertas automáticos diante de desvios",
      "solutions.processes.title": "Processos que fluem",
      "solutions.processes.body": "Automatizamos tarefas com RPA e desenvolvemos rotinas com Arduino para que sua equipe ganhe tempo.",
      "solutions.processes.bullet1": "Fluxos que conectam ERP, CRM e WMS",
      "solutions.processes.bullet2": "Controle de estoque e RMA em um clique",
      "solutions.processes.bullet3": "Acompanhamento proativo de ocorrências",
      "solutions.infrastructure.title": "Infraestrutura flexível",
      "solutions.infrastructure.body": "Implantamos em nossa nuvem gerenciada ou nos seus servidores, sempre com monitoramento e suporte contínuos.",
      "solutions.infrastructure.bullet1": "Implantações e operações controladas",
      "solutions.infrastructure.bullet2": "Backups e planos de recuperação",
      "solutions.infrastructure.bullet3": "Integração com suas políticas de segurança",
      "method.title": "Metodologia centrada na sua equipe",
      "method.body": "Trabalhamos juntos para que cada etapa seja clara, mensurável e previsível.",
      "method.diagnosis.title": "Escuta e diagnóstico",
      "method.diagnosis.body": "Entendemos sua operação, revisamos as fontes de dados e identificamos oportunidades de melhoria.",
      "method.plan.title": "Plano compartilhado",
      "method.plan.body": "Definimos marcos, responsáveis e indicadores de sucesso que toda a equipe pode acompanhar.",
      "method.implementation.title": "Implantação guiada",
      "method.implementation.body": "Executamos migrações, automações e desenvolvimentos com testes e acompanhamento diário.",
      "method.improvement.title": "Melhoria contínua",
      "method.improvement.body": "Monitoramos resultados, fazemos ajustes e transferimos conhecimento para que sua equipe trabalhe com autonomia.",
      "cta.title": "Pronto para acelerar seu projeto com segurança?",
      "cta.body": "Vamos conversar e criar um plano claro para sua migração, automação ou próximo desenvolvimento.",
      "cta.button": "Agendar uma conversa",
      "contact.eyebrow": "Vamos trabalhar juntos",
      "contact.title": "Conte o que você precisa resolver",
      "contact.body": "Deixe seus dados e um consultor entrará em contato em até 24 horas com próximos passos práticos.",
      "contact.bullet1": "Reunião inicial sem custo para entender seu contexto",
      "contact.bullet2": "Confidencialidade e respeito pelos seus dados",
      "contact.bullet3": "Equipe multidisciplinar à sua disposição",
      "contact.nameLabel": "Nome completo",
      "contact.namePlaceholder": "Seu nome",
      "contact.emailLabel": "E-mail",
      "contact.emailPlaceholder": "nome@empresa.com",
      "contact.companyLabel": "Empresa",
      "contact.companyPlaceholder": "Nome da sua empresa",
      "contact.interestTitle": "Tem interesse na Suite Lite?",
      "contact.interestBody": "Informe na mensagem qual produto você gostaria de conhecer.",
      "contact.projectLabel": "O que você precisa resolver?",
      "contact.projectPlaceholder": "Conhecer a Suite Lite, migrar dados, automatizar processos...",
      "contact.newsletter": "Quero receber ideias e novidades da devLink.",
      "contact.submit": "Quero meu diagnóstico",
      "contact.note": "Ao enviar, você aceita nossa política de privacidade e o uso responsável dos seus dados.",
      "footer.tagline": "Hospedamos e desenvolvemos soluções tecnológicas centradas nas pessoas.",
      "footer.contact": "Contato",
      "footer.follow": "Siga-nos",
      "footer.legal": "Legal",
      "footer.privacy": "Política de Privacidade",
      "footer.terms": "Termos de Serviço",
      "footer.copyright": "devLink. Todos os direitos reservados."
    }
  };

  const baseTranslations = {};
  let currentLanguage = DEFAULT_LANGUAGE;

  const rememberBaseTranslation = (key, value) => {
    if (key && baseTranslations[key] === undefined) {
      baseTranslations[key] = value;
    }
  };

  document.querySelectorAll("[data-i18n]").forEach(element => {
    rememberBaseTranslation(element.dataset.i18n, element.textContent.trim());
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
    rememberBaseTranslation(
      element.dataset.i18nPlaceholder,
      element.getAttribute("placeholder") || ""
    );
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach(element => {
    rememberBaseTranslation(
      element.dataset.i18nAriaLabel,
      element.getAttribute("aria-label") || ""
    );
  });
  document.querySelectorAll("[data-i18n-content]").forEach(element => {
    rememberBaseTranslation(
      element.dataset.i18nContent,
      element.getAttribute("content") || ""
    );
  });

  const normalizeLanguage = value => {
    if (!value || typeof value !== "string") {
      return null;
    }

    const normalized = value.trim().toLowerCase().replace("_", "-");
    if (normalized === "pt" || normalized.startsWith("pt-")) {
      return "pt-BR";
    }
    if (normalized === "en" || normalized.startsWith("en-")) {
      return "en";
    }
    if (normalized === "es" || normalized.startsWith("es-")) {
      return "es";
    }
    return null;
  };

  const readStoredLanguage = () => {
    try {
      return normalizeLanguage(window.localStorage.getItem(STORAGE_KEY));
    } catch (error) {
      return null;
    }
  };

  const storeLanguage = language => {
    try {
      window.localStorage.setItem(STORAGE_KEY, language);
    } catch (error) {
      // Storage can be unavailable in private browsing or restricted embeds.
    }
  };

  const readQueryLanguage = () => {
    try {
      return normalizeLanguage(new URLSearchParams(window.location.search).get("lang"));
    } catch (error) {
      return null;
    }
  };

  const detectBrowserLanguage = () => {
    const candidates = Array.isArray(navigator.languages) && navigator.languages.length
      ? navigator.languages
      : [navigator.language];

    for (const candidate of candidates) {
      const language = normalizeLanguage(candidate);
      if (language) {
        return language;
      }
    }
    return DEFAULT_LANGUAGE;
  };

  const translate = key => {
    const localeTranslations = translations[currentLanguage] || {};
    return localeTranslations[key] ?? baseTranslations[key] ?? "";
  };

  const translateElement = element => {
    if (element.dataset.i18n) {
      element.textContent = translate(element.dataset.i18n);
    }
    if (element.dataset.i18nPlaceholder) {
      element.setAttribute("placeholder", translate(element.dataset.i18nPlaceholder));
    }
    if (element.dataset.i18nAriaLabel) {
      element.setAttribute("aria-label", translate(element.dataset.i18nAriaLabel));
    }
    if (element.dataset.i18nContent) {
      element.setAttribute("content", translate(element.dataset.i18nContent));
    }
  };

  const updateAddressLanguage = language => {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("lang", language);
      window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    } catch (error) {
      // The language still changes when History API access is restricted.
    }
  };

  const applyLanguage = (language, options = {}) => {
    const normalized = normalizeLanguage(language) || DEFAULT_LANGUAGE;
    if (!SUPPORTED_LANGUAGES.includes(normalized)) {
      return;
    }

    currentLanguage = normalized;
    document.documentElement.lang = normalized;
    document.documentElement.dataset.language = normalized;

    document.querySelectorAll(
      "[data-i18n], [data-i18n-placeholder], [data-i18n-aria-label], [data-i18n-content]"
    ).forEach(translateElement);

    document.querySelectorAll("[data-language-selector]").forEach(selector => {
      selector.value = normalized;
    });
    document.querySelectorAll("[data-language-field]").forEach(field => {
      field.value = normalized;
    });

    if (options.persist) {
      storeLanguage(normalized);
    }
    if (options.updateUrl) {
      updateAddressLanguage(normalized);
    }

    window.dispatchEvent(new CustomEvent("devlink:languagechange", {
      detail: { language: normalized }
    }));
  };

  const queryLanguage = readQueryLanguage();
  const initialLanguage = queryLanguage || readStoredLanguage() || detectBrowserLanguage();

  window.devLinkI18n = {
    applyLanguage,
    translateElement,
    translate,
    get language() {
      return currentLanguage;
    }
  };

  document.querySelectorAll("[data-language-selector]").forEach(selector => {
    selector.addEventListener("change", event => {
      applyLanguage(event.target.value, { persist: true, updateUrl: true });
    });
  });

  if (queryLanguage) {
    storeLanguage(queryLanguage);
  }
  applyLanguage(initialLanguage);
})();
