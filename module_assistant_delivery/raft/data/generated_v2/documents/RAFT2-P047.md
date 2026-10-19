# Note de cadrage - Café Jasmin

Document d'entraînement synthétique RAFT2-P047. Le client, les personnes et les chiffres sont fictifs.

### Contexte

Aujourd'hui, Café Jasmin gère ses réservations de table avec des tableurs et des appels téléphoniques. Ce projet livre un site de réservation de tables.

### Intervenants

Le client est Café Jasmin. L'adresse de contact projet du client est pm.raft2p047@example.com ; les urgences peuvent être signalées au +216 40 717 469. Le prestataire conçoit, développe, teste et déploie l'application.

### Périmètre

La première version devra : gérer les horaires d'ouverture et les jours de fermeture; annuler une réservation depuis le lien de confirmation; exporter les réservations du jour en CSV; recevoir une confirmation par SMS; permettre au personnel de voir les réservations du soir par table.

Ne font pas partie du projet : la livraison à domicile; le paiement en ligne par carte ; un programme de fidélité.

### Évolutions du périmètre

Les fonctionnalités non décrites ci-dessus sont traitées comme des demandes de modification. Le prestataire envoie une estimation sous 2 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

### Exigences essentielles

- La disponibilité mensuelle est d'au moins 99,5 %.
- Les données personnelles sont hébergées uniquement sur des serveurs situés dans l'Union européenne.
- Les mots de passe sont hachés avec Argon2id.
- Les pages destinées aux clients respectent le WCAG 2.2 niveau AA.

### Planning et paiements

- M1, à livrer à la fin de la semaine 3 : prototype cliquable et modèle de données. Paiement : 10 % du prix.
- M2, à livrer à la fin de la semaine 4 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 40 % du prix.
- M3, à livrer à la fin de la semaine 9 : back-office, notifications et rapport de tests. Paiement : 30 % du prix.
- M4, à livrer à la fin de la semaine 15 : mise en production et documentation de passation. Paiement : 20 % du prix.

### Recette

Le client dispose de 7 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 2 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

### Conditions contractuelles

Prix forfaitaire : 17 500 TND hors TVA, payé par jalon. Les factures sont payables sous 45 jours.

La propriété intellectuelle de l'application livrée est transférée au client après le paiement final. Garantie : le prestataire corrige sans frais les défauts signalés dans les 30 jours suivant la réception finale. Résiliation : chaque partie peut résilier avec un préavis écrit de 15 jours.

Les parties gardent les informations confidentielles pendant 2 ans après la fin du projet.

### Réunions

Un point d'avancement de 60 minutes a lieu chaque jeudi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

