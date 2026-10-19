# Notes de présentation

1. Présenter Cerebro comme un prototype académique complet, avec quatre usages IA et une architecture locale.
2. Relier les quatre problèmes produit aux quatre familles de modèles.
3. Expliquer que les objectifs portent autant sur la fiabilité et la mesure que sur l’automatisation.
4. Décrire le flux React vers gateway puis services, avec un seul serveur Ollama partagé.
5. Justifier FastAPI, XGBoost, scikit-learn, Gemma et RAG par leur rôle dans le projet.
6. Insister sur les datasets réels, les schémas, les licences et la provenance.
7. Décrire le protocole : préparation, split, baseline, modèle, test, artefact, endpoint.
8. Expliquer pourquoi Logistic Regression est un fallback transparent et efficace sur TF-IDF.
9. Montrer l’isolation du service fraude et rappeler le caractère advisory de la sortie.
10. Décrire le prompt structuré et le partage d’Ollama entre les deux services génératifs.
11. Lire les deux exemples réels et expliquer le temps de démarrage puis le temps à chaud.
12. Présenter M5 et les features historiques, calendaires et prix.
13. Comparer les trois méthodes sur le test intact, sans tuning sur le test.
14. Expliquer pourquoi WAPE est difficile à interpréter quand les ventes sont nulles.
15. Montrer le contrat d’entrée du service demand et la réponse 7 jours.
16. Décrire le principe RAG : récupérer d’abord, générer ensuite.
17. Montrer les références Amazon et le garde-fou de traçabilité.
18. Distinguer ce qui est déjà validé de l’amélioration RAG encore à mesurer.
19. Expliquer les avantages et le coût de l’isolation microservices.
20. Présenter le gateway comme contrat public et point de contrôle des timeouts.
21. Montrer que chaque app publie son OpenAPI 3.1.
22. Relier les chiffres de ressources aux décisions de sécurité.
23. Donner le total de 25 tests et le build Vite réussi.
24. Décrire les pages frontend et l’absence de faux résultats en cas d’erreur.
25. Être transparent : les appels HTTP sont prouvés, les captures UI sont bloquées par l’environnement.
26. Présenter les limites comme des éléments de validité scientifique.
27. Proposer les prochaines étapes sans prétendre qu’elles sont déjà réalisées.
28. Conclure sur l’intégration de modèles réels, de services indépendants et de mesures reproductibles.

Questions possibles : Pourquoi XGBoost ? Pourquoi WAPE est-il supérieur à 100% ? Comment éviter la fuite temporelle ? Pourquoi garder un gateway ? Comment empêcher Gemma d’inventer des attributs ? Que signifie advisory pour la fraude ?
