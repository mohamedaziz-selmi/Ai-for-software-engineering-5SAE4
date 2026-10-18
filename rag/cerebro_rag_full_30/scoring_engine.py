"""Canonical FICTIONAL dataset + deterministic scoring engine for the Cerebro RAG knowledge base.
All people, projects, reviews and numbers are synthetic and illustrative."""
from datetime import date

TODAY = date(2026, 10, 14)
CREATED = "2026-10-14"
VERSION = "1.0"

LEVELS = {1: "L1 Familiar", 2: "L2 Working", 3: "L3 Proficient", 4: "L4 Advanced"}

# ---------------------------------------------------------------- freelancers
# skills: (canonical skill, level, status, [project ids], evidence sentence)
FREELANCERS = {
 "FRE-001": dict(
  name="Lina Haddad", title="Full-Stack Developer (Angular + Spring Boot)", years=6, hpw=20, start="2026-11-02",
  doc="FRE-001_FullStack_Developer.pdf", comm="Replies within about 6 working hours (illustrative); weekly written status report in PRJ-001 and PRJ-002.",
  summary="Lina Haddad (FRE-001) is a fictional full-stack developer who builds Angular front ends and Spring Boot back ends on PostgreSQL. She is strongest at end-to-end feature delivery in medium-sized web products and has no documented evidence in machine learning or mobile development.",
  skills=[
   ("Angular",3,"verified",["PRJ-001","PRJ-002"],"Built the checkout and account modules in PRJ-001 with 14 component tests; built the job-posting wizard in PRJ-002."),
   ("TypeScript",3,"verified",["PRJ-001","PRJ-002"],"Typed models and service layer for the PRJ-001 checkout module; strict mode enabled in PRJ-002."),
   ("Spring Boot",3,"verified",["PRJ-001","PRJ-002","PRJ-006"],"Implemented the catalog service in PRJ-001, job services in PRJ-002 and the itinerary API in PRJ-006."),
   ("REST API design",3,"verified",["PRJ-001","PRJ-006"],"Published OpenAPI specifications for the catalog service (PRJ-001) and itinerary API (PRJ-006)."),
   ("PostgreSQL",3,"verified",["PRJ-001","PRJ-002","PRJ-006"],"Designed the catalog schema and Flyway migrations in PRJ-001; documented indexing choices in PRJ-002."),
   ("Docker",2,"verified",["PRJ-001"],"Wrote the docker-compose development environment in PRJ-001; no production container evidence."),
   ("Unit testing",2,"verified",["PRJ-001"],"Wrote 14 Angular component tests in PRJ-001; backend test coverage in PRJ-002 not documented."),
   ("Kubernetes",2,"claimed",[],"Listed on her profile; no project evidence exists in the dataset."),
   ("CI/CD",1,"claimed",[],"Mentions pipelines on her profile; PRJ-001 pipeline was built by FRE-005, not FRE-001."),
  ],
  limitations=["No documented machine learning, mobile or Kubernetes work.","Backend test coverage for PRJ-002 is not documented.","Docker use is limited to local development environments."],
  best_for=["Medium-size web applications that need Angular and Spring Boot from one person.","MVP or feature-module work with PostgreSQL schemas.","Client portals and administrative back-office tools."],
  unverified=["Kubernetes proficiency (claimed, no evidence).","CI/CD authoring (claimed, pipeline in PRJ-001 was authored by FRE-005)."],
  missing=["Production incident or on-call history.","Performance test results for her own services.","Any client review for work outside web development."]),
 "FRE-002": dict(
  name="Omar Belkacem", title="Frontend Angular Developer", years=5, hpw=30, start="2026-10-26",
  doc="FRE-002_Frontend_Angular_Developer.pdf", comm="Daily short written updates during PRJ-002; asked clarifying questions on 9 of 11 tickets (illustrative).",
  summary="Omar Belkacem (FRE-002) is a fictional frontend specialist whose strongest documented skills are Angular, TypeScript, RxJS and NgRx state management. He has no documented backend, database or DevOps evidence.",
  skills=[
   ("Angular",4,"verified",["PRJ-001","PRJ-002"],"Implemented product filtering, pagination and unit tests in PRJ-001; built the freelancer dashboard with lazy-loaded modules in PRJ-002."),
   ("TypeScript",4,"verified",["PRJ-001","PRJ-002"],"Defined shared typed contracts used by PRJ-002 dashboard components."),
   ("RxJS",3,"verified",["PRJ-001","PRJ-002"],"Used debounced RxJS streams for PRJ-001 search-as-you-type and for PRJ-002 dashboard polling."),
   ("NgRx",3,"verified",["PRJ-002"],"Introduced NgRx store, effects and selectors for the PRJ-002 proposals dashboard."),
   ("Unit testing",3,"verified",["PRJ-001","PRJ-002"],"Jasmine/Karma tests for the PRJ-001 filtering component and 31 tests for PRJ-002 selectors and effects."),
   ("Accessibility",2,"verified",["PRJ-002"],"Fixed keyboard navigation and label issues found in a partial PRJ-002 audit; no full WCAG audit documented."),
   ("Integration testing",2,"claimed",[],"End-to-end (Cypress) experience is claimed; no test artifacts exist in the dataset."),
  ],
  limitations=["No documented backend, database, DevOps or mobile evidence.","Accessibility evidence covers one audit pass only.","End-to-end testing is claimed but unverified."],
  best_for=["Angular single-page applications and dashboards.","State-heavy interfaces using NgRx.","Front-end refactoring and component test coverage."],
  unverified=["Cypress end-to-end testing (claimed)."],
  missing=["Any backend work.","Performance profiling results for Angular bundle size.","Evidence of working with design systems at scale."]),
 "FRE-003": dict(
  name="Sofia Marenko", title="Backend Spring Boot Developer", years=7, hpw=20, start="2026-11-09",
  doc="FRE-003_Backend_SpringBoot_Developer.pdf", comm="Written design notes before implementation; response time about 1 working day (illustrative).",
  summary="Sofia Marenko (FRE-003) is a fictional backend developer with the deepest documented Spring Boot and PostgreSQL evidence in the dataset, including query tuning, JWT security and integration tests. She has no documented frontend or machine learning implementation work.",
  skills=[
   ("Spring Boot",4,"verified",["PRJ-001","PRJ-002","PRJ-003","PRJ-004"],"Implemented the order and inventory services in PRJ-001, the proposal and escrow ledger services in PRJ-002, the gateway in PRJ-003 and the admin API in PRJ-004."),
   ("Spring Security",3,"verified",["PRJ-002","PRJ-004"],"Implemented JWT authentication and role checks in PRJ-002 and PRJ-004."),
   ("REST API design",4,"verified",["PRJ-001","PRJ-002","PRJ-004"],"Versioned APIs with documented error contracts in PRJ-002."),
   ("PostgreSQL",4,"verified",["PRJ-001","PRJ-002"],"Rewrote indexes for the PRJ-001 order-list query; illustrative latency fell from 1.8 s to 0.4 s."),
   ("Redis",2,"verified",["PRJ-001"],"Added session and catalog caching in PRJ-001; no cluster or eviction tuning documented."),
   ("Unit testing",3,"verified",["PRJ-002","PRJ-004"],"JUnit tests for ledger rules in PRJ-002."),
   ("Integration testing",3,"verified",["PRJ-002","PRJ-004"],"Testcontainers-based PostgreSQL integration tests in PRJ-002 and PRJ-004."),
   ("Docker",2,"verified",["PRJ-004"],"Wrote the Dockerfile for the PRJ-004 admin API; deployment was done by FRE-005."),
   ("Apache Kafka",2,"claimed",[],"Event streaming is claimed; no artifact exists in the dataset."),
  ],
  limitations=["No documented frontend implementation.","Escrow reconciliation defect in PRJ-002 remained open at closure.","Stated availability is limited to about 20 hours per week."],
  best_for=["Spring Boot REST back ends with PostgreSQL.","Database performance tuning and indexing reviews.","Secure API layers with JWT authentication."],
  unverified=["Apache Kafka experience (claimed)."],
  missing=["Python or machine learning implementation work.","Load-test results for services beyond PRJ-001.","Cloud deployment ownership."]),
 "FRE-004": dict(
  name="Daniel Okafor", title="AI/ML Engineer (Python, RAG)", years=6, hpw=30, start="2026-11-02",
  doc="FRE-004_AI_ML_Engineer.pdf", comm="Shares experiment logs weekly; communication is clear but documentation of failed experiments is thin (illustrative).",
  summary="Daniel Okafor (FRE-004) is a fictional AI/ML engineer with documented Python, scikit-learn, vector search and RAG pipeline work. His recommender in PRJ-003 was only partially successful, and his PyTorch work was never deployed.",
  skills=[
   ("Python",4,"verified",["PRJ-003","PRJ-004"],"Implemented data preparation, training and API code in PRJ-003 and the ingestion pipeline in PRJ-004."),
   ("scikit-learn",3,"verified",["PRJ-003"],"Built the collaborative-filtering baseline and offline evaluation in PRJ-003."),
   ("PyTorch",2,"verified",["PRJ-003"],"Ran a neural ranking experiment in PRJ-003; it was not deployed."),
   ("FastAPI",3,"verified",["PRJ-004"],"Built the retrieval and answer endpoints of PRJ-004."),
   ("Vector search",3,"verified",["PRJ-004"],"Configured ChromaDB collections and metadata filters in PRJ-004."),
   ("RAG pipeline",3,"verified",["PRJ-004"],"Implemented chunking, hybrid retrieval and citation output in PRJ-004."),
   ("LLM evaluation",2,"verified",["PRJ-004"],"Built a 60-question evaluation set in PRJ-004; no automated regression gate."),
   ("Docker",2,"verified",["PRJ-004"],"Containerized the PRJ-004 pipeline for local use; deployment was done by FRE-005."),
   ("Monitoring",2,"claimed",[],"Model monitoring is claimed; no dashboards exist in the dataset."),
  ],
  limitations=["PRJ-003 cold-start recommendations remained weak.","Evaluation set in PRJ-004 is small (60 questions).","No documented production model monitoring."],
  best_for=["Retrieval-augmented generation assistants over internal documents.","Prototype recommenders with offline evaluation.","Python APIs around ML components."],
  unverified=["Model monitoring and MLOps (claimed)."],
  missing=["Production-scale training evidence.","Fine-tuning of language models.","Frontend or mobile integration work."]),
 "FRE-005": dict(
  name="Priya Raman", title="DevOps and Cloud Engineer", years=8, hpw=25, start="2026-10-28",
  doc="FRE-005_DevOps_Cloud_Engineer.pdf", comm="Runbook-style handover documents; responds in about 4 working hours (illustrative).",
  summary="Priya Raman (FRE-005) is a fictional DevOps engineer with documented Docker, CI/CD, Terraform and AWS evidence. Her Kubernetes migration in PRJ-005 reached staging but production cut-over was left unfinished.",
  skills=[
   ("Docker",4,"verified",["PRJ-001","PRJ-004","PRJ-005"],"Multi-stage images and image scanning gates across PRJ-001, PRJ-004 and PRJ-005."),
   ("Kubernetes",3,"verified",["PRJ-005"],"Migrated services to a staging cluster in PRJ-005; production migration unresolved."),
   ("CI/CD",4,"verified",["PRJ-001","PRJ-005"],"Authored the GitHub Actions pipelines for PRJ-001 and PRJ-005."),
   ("Terraform",3,"verified",["PRJ-005"],"Provisioned networking and compute modules for PRJ-005."),
   ("AWS",3,"verified",["PRJ-005"],"Designed the PRJ-005 environment on AWS with separate staging and production accounts."),
   ("Monitoring",3,"verified",["PRJ-005"],"Prometheus and Grafana dashboards with alert rules for PRJ-005."),
   ("Security scanning",2,"claimed",[],"Security scanning in pipelines is claimed; PRJ-001 scan reports are not in the dataset."),
  ],
  limitations=["PRJ-005 production Kubernetes cut-over was not completed.","No documented application-code work.","Cost optimization is not evidenced."],
  best_for=["Containerization and CI/CD pipeline setup.","Cloud environment provisioning with Terraform.","Staging-first Kubernetes migrations."],
  unverified=["Security scanning in CI pipelines (claimed)."],
  missing=["Disaster recovery test records.","Multi-cloud experience.","Cost reports for deployed environments."]),
 "FRE-006": dict(
  name="Mateo Alvarez", title="Mobile Developer (Flutter)", years=4, hpw=28, start="2026-11-02",
  doc="FRE-006_Mobile_Flutter_Developer.pdf", comm="Demo builds delivered every two weeks; occasional late replies on weekends (illustrative).",
  summary="Mateo Alvarez (FRE-006) is a fictional mobile developer with documented Flutter and Dart delivery in PRJ-006, including push notifications and offline storage. Offline synchronization conflicts remained partly unresolved and no iOS store release is documented.",
  skills=[
   ("Flutter",3,"verified",["PRJ-006"],"Built the itinerary, map and booking screens in PRJ-006 and published an Android internal-testing build."),
   ("Dart",3,"verified",["PRJ-006"],"Wrote the Dart domain layer and repositories for PRJ-006."),
   ("Offline storage",2,"verified",["PRJ-006"],"Local SQLite storage for itineraries in PRJ-006; sync conflicts were not fully resolved."),
   ("Firebase push",2,"verified",["PRJ-006"],"Implemented Firebase Cloud Messaging notifications for itinerary changes in PRJ-006."),
   ("Unit testing",2,"verified",["PRJ-006"],"Widget and unit tests for the PRJ-006 booking flow; coverage figure not documented."),
   ("Native mobile",2,"claimed",[],"Native Android/iOS module experience is claimed; no artifact exists in the dataset."),
  ],
  limitations=["Offline sync conflict handling in PRJ-006 was incomplete.","No documented iOS store release.","Backend work was done by FRE-001, not FRE-006."],
  best_for=["Flutter apps with REST back ends.","Prototype-to-beta mobile products.","Push notification flows."],
  unverified=["Native Android/iOS module development (claimed)."],
  missing=["iOS App Store submission history.","Performance profiling on low-end devices.","Accessibility testing on mobile."]),
}

# ---------------------------------------------------------------- projects
PROJECTS = {
 "PRJ-001": dict(name="Souk Nova Online Marketplace Storefront", client="Souk Nova Retail (fictional)", domain="ecommerce", cx=2, end=(2024,6),
  doc="PRJ-001_Ecommerce_Platform.pdf", outcome="success", weeks_planned=16, weeks_actual=17, budget=38000,
  tech=["Angular","TypeScript","Spring Boot","PostgreSQL","Redis","Docker","GitHub Actions"],
  team={"FRE-001":("contributor","Checkout and account modules in Angular; catalog service in Spring Boot; catalog schema and Flyway migrations."),
        "FRE-002":("contributor","Product filtering, pagination and search-as-you-type components in Angular with their unit tests."),
        "FRE-003":("lead","Order and inventory services in Spring Boot; Redis caching; PostgreSQL index rewrite for the order-list query."),
        "FRE-005":("contributor","GitHub Actions CI/CD pipeline and Docker image build; staging deployment scripts.")},
  context="Souk Nova Retail (fictional) wanted to replace a template shop with a custom storefront supporting 8,000 products, guest checkout and an order history page.",
  scope=["Product catalog with filtering and pagination.","Guest and registered checkout.","Order history and status tracking.","Admin inventory updates."],
  tech_req=["Response time under 1 second for the order list at 50,000 orders (illustrative target).","JWT-protected account endpoints.","Automated build and deployment to a staging environment."],
  arch="Single-page Angular application calling three Spring Boot services (catalog, orders, inventory) behind one gateway; PostgreSQL as system of record; Redis for catalog caching and sessions; GitHub Actions deploying Docker images to a staging host.",
  deliver=["Angular storefront (catalog, checkout, accounts).","Three Spring Boot services with OpenAPI documentation.","PostgreSQL schema with Flyway migrations.","CI/CD pipeline definition and staging runbook."],
  challenges=[("Slow order-list query at 50,000 seeded orders (1.8 s).","FRE-003 replaced a sequential scan with a composite index on customer and created date and paginated by keyset; the same query measured 0.4 s in the illustrative benchmark."),
              ("Filter combinations caused excessive API calls.","FRE-002 added debounced RxJS streams and cancelled in-flight requests with switchMap in the filtering component.")],
  testing="Component tests for filtering (FRE-002) and checkout (FRE-001); JUnit and Testcontainers integration tests for order services (FRE-003). Illustrative line coverage for backend services was 71 percent; frontend coverage was not measured.",
  outcome_txt="All four scope items were delivered to staging, one week late. The client accepted the project. Production go-live was performed by the client's own team and is outside the documented evidence.",
  limits=["No load test above 50,000 seeded orders.","Frontend test coverage was not measured.","Payment gateway integration used a sandbox only."],
  demonstrates=["Angular","TypeScript","RxJS","Spring Boot","PostgreSQL","Redis","CI/CD","Docker","Unit testing","Integration testing"],
  not_inferable=["Kubernetes","Production payment processing","Machine learning","Mobile development"],
  related=["FRE-001","FRE-002","FRE-003","FRE-005","TEC-001","TEC-002","TEC-003","EST-001","QUA-001"]),
 "PRJ-002": dict(name="TaskBridge Freelance Marketplace", client="TaskBridge Labs (fictional)", domain="marketplace", cx=3, end=(2025,2),
  doc="PRJ-002_Freelance_Marketplace.pdf", outcome="partial", weeks_planned=20, weeks_actual=26, budget=61000,
  tech=["Angular","TypeScript","NgRx","Spring Boot","Spring Security","PostgreSQL","Docker"],
  team={"FRE-001":("contributor","Job-posting wizard in Angular and job services in Spring Boot."),
        "FRE-002":("contributor","Freelancer proposals dashboard in Angular using NgRx; accessibility fixes."),
        "FRE-003":("lead","Proposal service, escrow ledger, JWT security and integration tests.")},
  context="TaskBridge Labs (fictional) wanted a marketplace where clients post jobs, freelancers submit proposals and payments are held in an escrow ledger until milestones are approved.",
  scope=["Job posting with required skills and budget.","Proposal submission and comparison dashboard.","Escrow ledger with milestone release.","Role-based access for clients, freelancers and administrators."],
  tech_req=["JWT authentication with role-based authorization.","Ledger entries must be immutable and reconcilable.","Dashboard must update proposals without a full page reload."],
  arch="Angular application with NgRx store; Spring Boot services for jobs, proposals and escrow; PostgreSQL with double-entry ledger tables; Docker compose for development.",
  deliver=["Job, proposal and escrow services.","Angular client and freelancer dashboards.","Integration test suite for ledger rules.","API documentation."],
  challenges=[("Duplicate proposal submissions when users double-clicked.","FRE-003 added an idempotency key to the proposal endpoint; FRE-002 disabled the submit action while the request was pending."),
              ("Escrow reconciliation produced a mismatch of 0.4 percent of test transactions.","Root cause was not isolated before closure; the defect was logged as open.")],
  testing="31 NgRx unit tests (FRE-002); Testcontainers integration tests for the ledger (FRE-003). Accessibility audit was partial.",
  outcome_txt="Jobs, proposals and dashboards were delivered. Escrow release shipped behind a feature flag because the reconciliation defect remained open. Delivery was six weeks late. The client also changed the escrow release rules during the project, which contributed to the delay.",
  limits=["Escrow reconciliation defect unresolved.","Accessibility audit incomplete.","No production deployment evidence."],
  demonstrates=["Angular","NgRx","TypeScript","Spring Boot","Spring Security","PostgreSQL","Integration testing","Accessibility"],
  not_inferable=["Payment provider integration in production","Kubernetes","Machine learning","Cloud cost management"],
  related=["FRE-001","FRE-002","FRE-003","TEC-001","TEC-002","TEC-003","EST-005","EST-006","QUA-002"]),
 "PRJ-003": dict(name="ShopSense Product Recommendation Engine", client="ShopSense Retail Group (fictional)", domain="ai", cx=2, end=(2024,11),
  doc="PRJ-003_AI_Recommendation_System.pdf", outcome="partial", weeks_planned=10, weeks_actual=12, budget=24000,
  tech=["Python","scikit-learn","PyTorch","Spring Boot","PostgreSQL"],
  team={"FRE-004":("lead","Data preparation, collaborative-filtering baseline, offline evaluation and the PyTorch ranking experiment."),
        "FRE-003":("contributor","Spring Boot gateway that calls the recommender service and logs impressions.")},
  context="ShopSense Retail Group (fictional) wanted a 'customers also bought' recommender for an existing store with 120,000 purchase events.",
  scope=["Item-to-item recommendations for existing customers.","Offline evaluation report.","Gateway endpoint for the storefront."],
  tech_req=["Offline precision at 10 reported against a popularity baseline.","Recommendation endpoint latency under 200 ms (illustrative target).","Impression logging for later analysis."],
  arch="Python batch training job writing item-similarity tables to PostgreSQL; a Spring Boot gateway reading those tables and logging impressions.",
  deliver=["Training pipeline and similarity tables.","Offline evaluation report.","Spring Boot gateway endpoint."],
  challenges=[("Cold-start items had no purchase history.","FRE-004 added a content-based fallback using product category; results remained weak and were documented as a limitation."),
              ("Neural ranking experiment gave only marginal gains.","FRE-004 documented that the PyTorch model improved offline precision by 2 points but was not deployed because of added complexity.")],
  testing="Offline evaluation with a time-based split; gateway integration tests by FRE-003. No online A/B test was run.",
  outcome_txt="Warm-start recommendations beat the popularity baseline in offline evaluation. Cold-start performance was weak and no online experiment was run.",
  limits=["No online A/B evidence.","Cold-start weakness.","PyTorch model not deployed."],
  demonstrates=["Python","scikit-learn","PyTorch","Spring Boot","PostgreSQL","Integration testing"],
  not_inferable=["Production model monitoring","Large-scale training","RAG","Mobile development"],
  related=["FRE-003","FRE-004","TEC-004","TEC-003","EST-003","QUA-004"]),
 "PRJ-004": dict(name="DocuPilot RAG Knowledge Assistant", client="Northwind Compliance Advisors (fictional)", domain="ai", cx=3, end=(2025,9),
  doc="PRJ-004_RAG_Knowledge_Assistant.pdf", outcome="success", weeks_planned=12, weeks_actual=13, budget=42000,
  tech=["Python","FastAPI","ChromaDB","Spring Boot","Spring Security","Docker","GitHub Actions"],
  team={"FRE-004":("lead","Ingestion pipeline, chunking, hybrid retrieval, answer endpoint with citations, evaluation set."),
        "FRE-003":("contributor","Spring Boot admin API with JWT authentication for document management."),
        "FRE-005":("contributor","Containerized deployment and CI/CD for the pipeline and admin API.")},
  context="Northwind Compliance Advisors (fictional) wanted staff to ask questions about 1,200 internal policy documents and receive answers with citations.",
  scope=["Document ingestion for PDF and DOCX.","Hybrid (semantic + keyword) retrieval.","Answers with source citations.","Admin interface for document management."],
  tech_req=["Every answer must cite retrieved passages.","Metadata filtering by department and document type.","Authenticated admin operations."],
  arch="FastAPI service performing ingestion, embedding and retrieval against ChromaDB; Spring Boot admin API for document metadata; Docker images deployed by a GitHub Actions pipeline.",
  deliver=["Ingestion and retrieval service.","Admin API.","60-question evaluation set with expected source documents.","Deployment pipeline."],
  challenges=[("Tables in PDFs were split across chunks and lost meaning.","FRE-004 introduced section-aware chunking and repeated table captions in each chunk."),
              ("Answers sometimes cited the wrong document version.","FRE-004 added version metadata filters; the issue dropped from 7 of 60 to 2 of 60 evaluation questions.")],
  testing="Retrieval evaluated with Recall@5 on 60 questions (illustrative result 0.88). Integration tests for the admin API by FRE-003. No automated regression gate.",
  outcome_txt="The assistant was accepted by the client. Two evaluation questions still cited a superseded policy version. Deployment succeeded to a single container host.",
  limits=["Evaluation set is small.","Superseded-version citations in 2 of 60 questions.","No load test."],
  demonstrates=["Python","FastAPI","Vector search","RAG pipeline","LLM evaluation","Spring Boot","Spring Security","Docker","CI/CD"],
  not_inferable=["Language model fine-tuning","Kubernetes","Large-scale vector index operations","Frontend development"],
  related=["FRE-003","FRE-004","FRE-005","TEC-004","TEC-002","TEC-005","EVA-005","QUA-002"]),
 "PRJ-005": dict(name="LaunchPad Cloud Deployment Platform", client="Brightline Software (fictional)", domain="cloud", cx=2, end=(2025,5),
  doc="PRJ-005_Cloud_Deployment_Platform.pdf", outcome="partial", weeks_planned=8, weeks_actual=10, budget=21000,
  tech=["Docker","Kubernetes","Terraform","AWS","GitHub Actions","Prometheus","Grafana"],
  team={"FRE-005":("lead","Terraform modules, AWS accounts, GitHub Actions pipelines, staging Kubernetes cluster and monitoring.")},
  context="Brightline Software (fictional) wanted its five internal services moved from manually managed virtual machines to a repeatable cloud deployment.",
  scope=["Infrastructure as code for staging and production.","Container builds and automated deployments.","Kubernetes staging cluster.","Monitoring and alerting."],
  tech_req=["Reproducible environments from code.","Deployments without manual server access.","Alerting on error rate and latency."],
  arch="Terraform modules for networking and compute on AWS; GitHub Actions building Docker images; staging Kubernetes cluster; Prometheus and Grafana for metrics.",
  deliver=["Terraform modules.","CI/CD pipelines.","Staging cluster with all five services.","Dashboards and alert rules."],
  challenges=[("Stateful service did not tolerate pod restarts.","FRE-005 documented the limitation and kept that service on a virtual machine; production cut-over was deferred."),
              ("Pipeline duration exceeded 25 minutes.","FRE-005 introduced layer caching and parallel test jobs, reducing duration to about 11 minutes (illustrative).")],
  testing="Smoke tests after each staging deployment; no chaos or failover tests.",
  outcome_txt="Infrastructure as code, pipelines and the staging cluster were delivered. Production Kubernetes migration was not completed.",
  limits=["Production cut-over not completed.","No failover testing.","No cost report."],
  demonstrates=["Docker","Kubernetes","Terraform","AWS","CI/CD","Monitoring"],
  not_inferable=["Production Kubernetes operations","Application development","Disaster recovery","Cost optimization"],
  related=["FRE-005","TEC-005","EST-004","EST-005","QUA-005"]),
 "PRJ-006": dict(name="RoamLite Mobile Travel Companion", client="RoamLite Travel (fictional)", domain="mobile", cx=2, end=(2025,12),
  doc="PRJ-006_Mobile_Travel_Application.pdf", outcome="partial", weeks_planned=14, weeks_actual=17, budget=33000,
  tech=["Flutter","Dart","SQLite","Firebase Cloud Messaging","Spring Boot","PostgreSQL"],
  team={"FRE-006":("lead","Flutter application: itinerary, map and booking screens, offline storage, push notifications."),
        "FRE-001":("contributor","Spring Boot itinerary API, PostgreSQL schema and OpenAPI contract.")},
  context="RoamLite Travel (fictional) wanted a mobile app that shows trip itineraries, works offline during flights and sends push notifications when bookings change.",
  scope=["Itinerary and booking screens.","Offline access to saved itineraries.","Push notifications.","Itinerary API."],
  tech_req=["Offline read access to itineraries.","Notifications within one minute of a change (illustrative target).","Android and iOS builds."],
  arch="Flutter application with a local SQLite cache; Spring Boot itinerary API on PostgreSQL; Firebase Cloud Messaging for notifications.",
  deliver=["Flutter application.","Itinerary API with OpenAPI contract.","Android internal-testing build."],
  challenges=[("Offline edits conflicted with server updates.","FRE-006 implemented last-write-wins with a visible conflict banner; full merge logic remained unresolved."),
              ("Map screen was slow on older devices.","FRE-006 reduced marker rebuilds with memoized widgets; no low-end device benchmark was recorded.")],
  testing="Widget and unit tests for the booking flow (FRE-006); API tests for the itinerary API (FRE-001). No device-farm testing.",
  outcome_txt="The Android internal-testing build was delivered. iOS release was not performed and offline conflict resolution was partial. Delivery was three weeks late.",
  limits=["iOS release not documented.","Offline conflict resolution partial.","No low-end device benchmark."],
  demonstrates=["Flutter","Dart","Offline storage","Firebase push","Unit testing","Spring Boot","REST API design","PostgreSQL"],
  not_inferable=["iOS App Store release","Native module development","Accessibility on mobile","Large-scale backend operations"],
  related=["FRE-001","FRE-006","TEC-006","TEC-002","EST-002","QUA-003"]),
}

# ---------------------------------------------------------------- reviews (fictional)
REVIEWS = [
 ("REV-001","FRE-001","PRJ-001",5,"2024-07-02","specific","Delivered the checkout flow with clear component tests and explained schema decisions in writing."),
 ("REV-002","FRE-001","PRJ-002",4,"2025-03-10","specific","Job-posting wizard worked as specified; two validation edge cases were fixed after review."),
 ("REV-003","FRE-001","PRJ-006",4,"2026-01-12","mixed","Itinerary API contract was clear. Response times varied during the second month."),
 ("REV-004","FRE-002","PRJ-001",5,"2024-07-02","specific","Filtering component handled combined filters smoothly and shipped with unit tests."),
 ("REV-005","FRE-002","PRJ-002",5,"2025-03-11","specific","Dashboard state handling with NgRx was easy to extend; keyboard navigation issues were fixed quickly."),
 ("REV-006","FRE-002","PRJ-002",3,"2025-03-12","vague","Good developer but communication style was not my favourite."),
 ("REV-007","FRE-003","PRJ-001",5,"2024-07-03","specific","Order list query dropped from about 1.8 s to 0.4 s after the index change, documented in a short note."),
 ("REV-008","FRE-003","PRJ-002",4,"2025-03-10","mixed","Ledger rules were well tested; the 0.4 percent reconciliation mismatch was still open at handover."),
 ("REV-009","FRE-003","PRJ-004",5,"2025-10-05","specific","Admin API with JWT roles was delivered on schedule with integration tests."),
 ("REV-010","FRE-004","PRJ-003",3,"2024-12-01","mixed","Baseline beat the popularity baseline offline; cold-start results were weaker than hoped."),
 ("REV-011","FRE-004","PRJ-004",5,"2025-10-05","specific","Citations traced to the right passages in 58 of 60 evaluation questions and the evaluation set was documented."),
 ("REV-012","FRE-004","PRJ-004",4,"2025-10-07","specific","Chunking fix for tables made a visible difference; wished for an automated regression check."),
 ("REV-013","FRE-005","PRJ-001",4,"2024-07-02","specific","Pipeline built and deployed to staging on the first day of the sprint; image scan reports were not shared."),
 ("REV-014","FRE-005","PRJ-004",5,"2025-10-06","specific","Deployment runbook was clear and a rollback was rehearsed once."),
 ("REV-015","FRE-005","PRJ-005",3,"2025-06-02","mixed","Staging migration was solid, but the production cut-over was deferred and we needed a follow-up contract."),
 ("REV-016","FRE-006","PRJ-006",4,"2026-01-13","specific","Android build installed cleanly and notifications arrived within seconds in testing."),
 ("REV-017","FRE-006","PRJ-006",3,"2026-01-14","mixed","Offline conflicts still lose edits in rare cases; the conflict banner is helpful but not a fix."),
 ("REV-018","FRE-006","PRJ-006",2,"2026-01-20","vague","Not what I imagined. Felt slow."),
]

# delivery records: (id, freelancer, project, planned_weeks_for_component, actual_weeks, milestones_on_time, milestones_total, post_release_defects)
DELIVERY = [
 ("DEL-001","FRE-001","PRJ-001",10,10,4,4,2),("DEL-002","FRE-002","PRJ-001",6,6,3,3,1),
 ("DEL-003","FRE-003","PRJ-001",14,15,5,6,3),("DEL-004","FRE-005","PRJ-001",3,3,2,2,0),
 ("DEL-005","FRE-001","PRJ-002",8,10,3,5,3),("DEL-006","FRE-002","PRJ-002",9,10,4,5,1),
 ("DEL-007","FRE-003","PRJ-002",18,24,4,8,4),("DEL-008","FRE-004","PRJ-003",10,12,3,5,2),
 ("DEL-009","FRE-003","PRJ-003",3,3,2,2,0),("DEL-010","FRE-004","PRJ-004",11,12,5,6,2),
 ("DEL-011","FRE-003","PRJ-004",4,4,3,3,0),("DEL-012","FRE-005","PRJ-004",3,3,2,2,0),
 ("DEL-013","FRE-005","PRJ-005",8,10,4,6,1),("DEL-014","FRE-006","PRJ-006",14,17,4,7,3),
 ("DEL-015","FRE-001","PRJ-006",5,5,3,3,1),
]

# ---------------------------------------------------------------- jobs & proposals (fictional integration-test data)
# job: title, req [(skill, mandatory)], opt, domain, cx, pref, hard, D weeks, deadline_type, effort hrs, ref weeks
JOBS = {
 "JOB-001":dict(title="B2B ordering portal (Angular + Spring Boot)",req=[("Angular",True),("Spring Boot",True),("PostgreSQL",False)],opt=["Docker","Unit testing"],domain="ecommerce",cx=2,pref=9000,hard=11000,D=12,dt="soft",effort=420,ref=14),
 "JOB-002":dict(title="Analytics dashboard front end",req=[("Angular",True),("TypeScript",False),("RxJS",False)],opt=["NgRx","Accessibility"],domain="saas",cx=1,pref=4000,hard=5000,D=6,dt="hard",effort=200,ref=8),
 "JOB-003":dict(title="RAG assistant for company documents",req=[("Python",True),("RAG pipeline",True),("Vector search",False),("FastAPI",False)],opt=["LLM evaluation","Docker"],domain="ai",cx=3,pref=12000,hard=15000,D=10,dt="soft",effort=480,ref=14),
 "JOB-004":dict(title="Kubernetes migration with CI/CD",req=[("Docker",True),("Kubernetes",True),("CI/CD",False),("Terraform",False)],opt=["Monitoring","AWS"],domain="cloud",cx=2,pref=7000,hard=9000,D=8,dt="hard",effort=240,ref=9),
 "JOB-005":dict(title="Flutter fitness booking app",req=[("Flutter",True),("Dart",False)],opt=["Offline storage","Firebase push","Unit testing"],domain="mobile",cx=2,pref=8000,hard=10000,D=10,dt="soft",effort=380,ref=12),
 "JOB-006":dict(title="Retail recommendation engine",req=[("Python",True),("scikit-learn",True),("FastAPI",False)],opt=["PyTorch","Spring Boot"],domain="ai",cx=2,pref=9000,hard=12000,D=9,dt="soft",effort=320,ref=11),
 "JOB-007":dict(title="Marketplace platform MVP",req=[("Spring Boot",True),("Angular",True),("PostgreSQL",False),("REST API design",False)],opt=["Docker","Unit testing","CI/CD"],domain="marketplace",cx=3,pref=15000,hard=19000,D=16,dt="soft",effort=800,ref=22),
 "JOB-008":dict(title="API performance and database tuning",req=[("Spring Boot",True),("PostgreSQL",True)],opt=["Redis","Unit testing"],domain="ecommerce",cx=1,pref=3500,hard=4500,D=5,dt="hard",effort=120,ref=5),
 "JOB-009":dict(title="E-commerce storefront refresh",req=[("Angular",True),("TypeScript",False),("Unit testing",False),("Accessibility",False)],opt=["Spring Boot"],domain="ecommerce",cx=2,pref=6000,hard=7500,D=8,dt="soft",effort=260,ref=9),
 "JOB-010":dict(title="CI/CD pipeline and container hardening",req=[("Docker",True),("CI/CD",True)],opt=["Security scanning","Monitoring"],domain="cloud",cx=1,pref=4000,hard=5000,D=6,dt="soft",effort=140,ref=6),
}
# proposal: (job, freelancer, price, weeks, hours/week, excluded_scope_cost, upfront_pct)
PROPOSALS_RAW = [
 ("JOB-001","FRE-001",9800,13,20,0,30),("JOB-001","FRE-003",10200,12,15,0,40),("JOB-001","FRE-002",5200,10,30,0,50),("JOB-001","FRE-006",4800,6,28,0,60),
 ("JOB-002","FRE-002",4300,6,30,0,30),("JOB-002","FRE-001",4000,7,20,0,30),("JOB-002","FRE-003",3200,6,15,0,40),("JOB-002","FRE-006",5600,7,28,0,30),
 ("JOB-003","FRE-004",13500,11,30,0,30),("JOB-003","FRE-003",9000,10,15,0,30),("JOB-003","FRE-005",11000,9,25,0,30),
 ("JOB-004","FRE-005",8200,8,25,0,30),("JOB-004","FRE-001",6500,8,20,0,40),("JOB-004","FRE-003",7500,9,20,0,30),
 ("JOB-005","FRE-006",8800,11,28,0,30),("JOB-005","FRE-002",7000,10,30,0,30),("JOB-005","FRE-001",3500,5,20,0,60),
 ("JOB-006","FRE-004",10500,9,30,0,30),("JOB-006","FRE-003",8000,9,15,0,30),
 ("JOB-007","FRE-001",16500,18,20,0,30),("JOB-007","FRE-003",14000,16,15,0,30),("JOB-007","FRE-002",9000,14,30,0,30),
 ("JOB-008","FRE-003",3800,5,20,0,30),("JOB-008","FRE-001",3200,4,20,0,30),("JOB-008","FRE-005",4000,5,25,0,30),
 ("JOB-009","FRE-002",6200,8,30,0,30),("JOB-009","FRE-001",6800,9,20,900,30),
 ("JOB-010","FRE-005",4200,6,20,0,30),("JOB-010","FRE-001",3000,4,20,0,50),("JOB-010","FRE-004",3800,6,20,0,30),
]
PROPOSALS = [dict(id=f"PRP-{i+1:03d}",job=j,fre=f,price=p,weeks=w,hpw=h,excl=e,upfront=u) for i,(j,f,p,w,h,e,u) in enumerate(PROPOSALS_RAW)]

# ---------------------------------------------------------------- scoring configuration
DEFAULT_WEIGHTS = {"skill":0.30,"budget":0.25,"deadline":0.20,"experience":0.15,"reviews":0.10}
CRIT_NAMES = {"skill":"Technical skill match","budget":"Budget compatibility","deadline":"Deadline compatibility","experience":"Relevant experience","reviews":"Reviews and reputation"}
MANDATORY_LEVEL, DEFAULT_LEVEL = 3, 2
RELATED = {  # skill -> verified related skills that give INDIRECT evidence (credit 0.5)
 "Kubernetes":["Docker"],"RxJS":["Angular"],"NgRx":["RxJS"],"TypeScript":["Angular"],"FastAPI":["Python"],
 "scikit-learn":["PyTorch"],"PyTorch":["scikit-learn"],"RAG pipeline":["Vector search"],"Vector search":["RAG pipeline"],
 "Dart":["Flutter"],"REST API design":["Spring Boot","FastAPI"],"Spring Boot":["Spring Security"],
 "Integration testing":["Unit testing"],"Unit testing":["Integration testing"],"Terraform":["AWS"],
}
CREDIT = {"direct":1.0,"direct-lower-level":0.6,"indirect":0.5,"unsupported-claim":0.25,"missing":0.0}
DOMAIN_RELATED = {frozenset(("ecommerce","marketplace")):0.5,frozenset(("marketplace","saas")):0.5,frozenset(("ecommerce","saas")):0.5,frozenset(("ai","saas")):0.3}
ROLE_W = {"lead":1.0,"contributor":0.7,"minor":0.4}
OUTCOME_W = {"success":1.0,"partial":0.85}
PRIOR, K = 60.0, 3

def _skill_map(fid):
    return {s[0]:s for s in FREELANCERS[fid]["skills"]}

def skill_credit(fid, skill, req_level):
    sm = _skill_map(fid); best = ("missing", 0.0, "No evidence for this skill in the dataset.")
    def upd(kind, note):
        nonlocal best
        if CREDIT[kind] > best[1]: best = (kind, CREDIT[kind], note)
    if skill in sm:
        _, lvl, st, prj, ev = sm[skill]
        if st == "verified":
            upd("direct" if lvl >= req_level else "direct-lower-level", f"Verified {LEVELS[lvl]} via {', '.join(prj)}")
        else:
            upd("unsupported-claim", "Claimed without evidence")
    for r in RELATED.get(skill, []):
        if r in sm and sm[r][2] == "verified" and sm[r][1] >= 2:
            upd("indirect", f"Related verified skill {r} ({LEVELS[sm[r][1]]})")
    return best

def score_skills(fid, job):
    num = den = 0.0; flags = []; detail = []; hold = False
    for sk, mand in job["req"]:
        lvl = MANDATORY_LEVEL if mand else DEFAULT_LEVEL; w = 2.0
        kind, c, note = skill_credit(fid, sk, lvl)
        num += w*c; den += w; detail.append((sk, "required" + ("/mandatory" if mand else ""), kind, c))
        if mand and c < 0.6:
            hold = True; flags.append(f"Mandatory skill {sk} lacks sufficient evidence ({kind})")
        elif kind == "unsupported-claim": flags.append(f"{sk} is claimed without evidence")
    for sk in job["opt"]:
        kind, c, note = skill_credit(fid, sk, DEFAULT_LEVEL)
        num += 1.0*c; den += 1.0; detail.append((sk, "optional", kind, c))
    return round(100*num/den, 1), detail, flags, hold

def score_budget(p, job):
    adj = p["price"] + p["excl"]; pref, hard = job["pref"], job["hard"]; flags = []; inelig = False
    if adj <= pref:
        s = 100.0
        if adj < 0.6*pref: s = 80.0; flags.append("Price is below 60% of the preferred maximum; verify scope before treating as value")
    elif adj <= hard:
        s = 100 - 50*(adj-pref)/(hard-pref)
    else:
        s = 0.0; inelig = True; flags.append("Adjusted price exceeds the hard budget limit")
    if p["upfront"] > 50: flags.append("Upfront payment above 50% of price")
    return round(s,1), adj, flags, inelig

def score_deadline(p, job, fid):
    T, D = p["weeks"], job["D"]; flags = []; inelig = False
    if T <= D: s = 100.0
    elif job["dt"] == "hard":
        s = 0.0; inelig = True; flags.append("Proposed duration exceeds the hard deadline")
    elif T <= 1.25*D: s = 100 - 50*(T-D)/(0.25*D)
    else: s = 0.0; flags.append("Proposed duration is more than 25% beyond the soft deadline")
    cap = 100.0
    if T < 0.6*job["ref"]:
        cap = min(cap, 70.0); flags.append("Duration is below 60% of the reference duration; fast delivery is not supported by evidence")
    capacity = p["hpw"]*T
    if capacity < 0.8*job["effort"]:
        cap = min(cap, 60.0); flags.append(f"Committed capacity ({capacity:.0f} h) is below 80% of estimated effort ({job['effort']} h)")
    if p["hpw"] > FREELANCERS[fid]["hpw"]:
        flags.append("Committed hours exceed stated availability")
    return round(min(s, cap),1), flags, inelig

def project_relevance(fid, prj, job):
    P = PROJECTS[prj]; sm = _skill_map(fid)
    ev = {s for s,(_,l,st,pr,_e) in sm.items() if st == "verified" and prj in pr}
    skills = [(s, 2.0) for s,_ in job["req"]] + [(s, 1.0) for s in job["opt"]]
    tot = sum(w for _,w in skills); got = sum(w for s,w in skills if s in ev)
    tech = got/tot
    if tech == 0: return 0.0, dict(tech=0)
    dom = 1.0 if P["domain"] == job["domain"] else DOMAIN_RELATED.get(frozenset((P["domain"], job["domain"])), 0.0)
    resp = ROLE_W[P["team"][fid][0]]
    d = abs(P["cx"]-job["cx"]); cx = {0:1.0,1:0.6}.get(d, 0.3)
    age = (TODAY.year - P["end"][0]) + (TODAY.month - P["end"][1])/12
    rec = 1.0 if age <= 1 else 0.95 if age <= 2 else 0.85 if age <= 3 else 0.7
    out = OUTCOME_W[P["outcome"]]
    r = (0.40*tech + 0.25*dom + 0.20*resp + 0.15*cx)*rec*out
    return r, dict(tech=tech, dom=dom, resp=resp, cx=cx, rec=rec, out=out, r=r)

def score_experience(fid, job):
    rs = []
    for prj, P in PROJECTS.items():
        if fid in P["team"]:
            r, d = project_relevance(fid, prj, job)
            if r > 0: rs.append((r, prj))
    rs.sort(reverse=True); top = [r for r,_ in rs[:3]] + [0,0,0]
    s = 100*(0.60*top[0] + 0.25*top[1] + 0.15*top[2])
    flags = []
    if len(rs) < 2: flags.append("Limited relevant project evidence (fewer than 2 relevant projects)")
    return round(s,1), rs[:3], flags

def score_reviews(fid):
    rv = [r for r in REVIEWS if r[1] == fid]
    if not rv: return None, 0, ["No reviews available; criterion not scored"]
    m = sum(r[3] for r in rv)/len(rv); base = (m-1)/4*100
    s = (len(rv)*base + K*PRIOR)/(len(rv)+K)
    flags = ["Small review sample (n<5)"] if len(rv) < 5 else []
    return round(s,1), len(rv), flags

def overall(scores, weights=None):
    w = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if sum(w.values()) <= 0: raise ValueError("weights must sum to more than zero")
    used = {k:v for k,v in w.items() if scores.get(k) is not None and v > 0}
    tw = sum(used.values())
    return round(sum(used[k]*scores[k] for k in used)/tw, 1), {k:v/tw for k,v in used.items()}

def evaluate(p, weights=None):
    job = JOBS[p["job"]]; fid = p["fre"]
    if weights is None: weights = job.get("w")
    sk, sd, sf, hold = score_skills(fid, job)
    bs, adj, bf, bi = score_budget(p, job)
    ds, df, di = score_deadline(p, job, fid)
    es, ex, ef = score_experience(fid, job)
    rs, n, rf = score_reviews(fid)
    scores = dict(skill=sk, budget=bs, deadline=ds, experience=es, reviews=rs)
    tot, nw = overall(scores, weights)
    flags = sf+bf+df+ef+rf
    if bi or di: status = "INELIGIBLE_HARD_CONSTRAINT"
    elif hold: status = "HOLD_PENDING_EVIDENCE"
    elif flags: status = "ELIGIBLE_WITH_FLAGS"
    else: status = "ELIGIBLE"
    return dict(scores=scores, overall=tot, status=status, flags=flags, adj_price=adj, n_reviews=n, detail=sd, exp_projects=ex)

SYNONYMS = {
 "Angular":["Angular 2+","Angular framework","Angular CLI"],"TypeScript":["TS"],"Spring Boot":["Spring","Spring Framework 6","Java backend"],
 "PostgreSQL":["Postgres","relational database","PSQL"],"Docker":["containers","containerization"],"Kubernetes":["K8s","container orchestration"],
 "CI/CD":["continuous integration","continuous delivery","GitHub Actions","pipelines"],"Terraform":["infrastructure as code","IaC"],
 "RAG pipeline":["retrieval-augmented generation","RAG"],"Vector search":["ChromaDB","embeddings search","semantic search"],
 "Python":["Python 3"],"scikit-learn":["sklearn","classical machine learning"],"Flutter":["Flutter SDK","cross-platform mobile"],
 "Dart":["Dart language"],"REST API design":["RESTful API","HTTP API","OpenAPI"],"Unit testing":["JUnit","Jasmine","Karma","widget tests"],
 "Integration testing":["Testcontainers","API tests"],"Redis":["in-memory cache"],"Monitoring":["observability","Prometheus","Grafana"],
}

JOBS["JOB-002"]["w"] = dict(skill=0.25, budget=0.20, deadline=0.35, experience=0.10, reviews=0.10)
JOBS["JOB-008"]["w"] = dict(skill=0.35, budget=0.30, deadline=0.20, experience=0.10, reviews=0.05)
