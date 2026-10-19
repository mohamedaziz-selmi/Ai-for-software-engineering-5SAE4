// Freelance briefs a visitor can start from. They are examples only: each one is written the way a client would
// describe the job, and is sent to the advisor unchanged.
export const advisorExamples = [
	{
		id: "fake-news",
		title: "Fake news detector",
		client: "Media start-up",
		budget: "$1,800",
		duration: "3 weeks",
		stack: ["Python", "scikit-learn", "Datasets"],
		brief:
			"A media start-up wants a system that classifies news articles as real or fake. Build it in Python with machine learning: train and evaluate a text classifier on a public English dataset, report accuracy and F1, and expose a small command line tool that takes an article and prints the verdict.",
	},
	{
		id: "bakery-shop",
		title: "Online bakery shop",
		client: "Local bakery",
		budget: "$2,400",
		duration: "4 weeks",
		stack: ["PHP", "Laravel", "Stripe"],
		brief:
			"A local bakery wants an online shop where customers browse cakes, add them to a cart and pay by card. Build it with Laravel and MySQL, integrate Stripe Checkout for payments and send an order confirmation email. Add a simple admin area to manage products and orders.",
	},
	{
		id: "booking-app",
		title: "Restaurant booking app",
		client: "Restaurant group",
		budget: "$3,200",
		duration: "6 weeks",
		stack: ["Flutter", "Firebase", "Mobile"],
		brief:
			"A restaurant group needs a mobile app for Android and iOS where guests book a table, pick a time slot and receive a push notification reminder. Build it with Flutter and Firebase (authentication, Firestore, cloud messaging) and include a staff screen that lists the day's reservations.",
	},
	{
		id: "review-sentiment-api",
		title: "Review sentiment API",
		client: "E-commerce agency",
		budget: "$1,200",
		duration: "2 weeks",
		stack: ["FastAPI", "Transformers", "REST"],
		brief:
			"An e-commerce agency wants a REST API that classifies the sentiment of customer reviews as positive, neutral or negative with a confidence score. Build it with FastAPI and a pretrained transformer model from Hugging Face, support batch requests, and document the endpoints with OpenAPI.",
	},
	{
		id: "real-estate-portal",
		title: "Real estate listings portal",
		client: "Property agency",
		budget: "$4,500",
		duration: "8 weeks",
		stack: ["Next.js", "PostgreSQL", "Maps"],
		brief:
			"A property agency wants a listings website where visitors search houses by city, price and number of rooms, see results on an interactive map and save favourites. Build it with Next.js and PostgreSQL, add image uploads for agents and make the pages fast and indexable by search engines.",
	},
	{
		id: "inventory-desktop",
		title: "Warehouse inventory system",
		client: "Logistics company",
		budget: "$3,800",
		duration: "7 weeks",
		stack: ["Java", "Spring Boot", "REST"],
		brief:
			"A logistics company needs an inventory system to track stock levels, incoming deliveries and low-stock alerts across two warehouses. Build the back end with Java and Spring Boot and a PostgreSQL database, secure it with role-based access, and export stock reports as CSV and PDF.",
	},
];
