# Contrat de prestation : une application web de réservation de cours pour Studio Atlas Fitness

Document d'entraînement synthétique RAFT2-P023. Le client, les personnes et les chiffres sont fictifs.

### Contexte et objectifs

Aujourd'hui, Studio Atlas Fitness gère ses réservations avec des tableurs et des appels téléphoniques. Ce projet livre une application web de réservation de cours.

### Parties et contacts

Le client est Studio Atlas Fitness. L'adresse de contact projet du client est pm.raft2p023@example.com ; les urgences peuvent être signalées au +216 52 839 837. Le prestataire conçoit, développe, teste et déploie l'application.

### Périmètre des travaux

Fonctionnalités prévues : permettre aux coachs de consulter la liste des participants; recevoir un e-mail de rappel 24 heures avant un cours; réserver et annuler un cours; consulter le planning hebdomadaire des cours; s'inscrire sur liste d'attente quand un cours est complet.

Sont expressément exclus de ce projet : la migration des données historiques; le paiement en ligne par carte ; un programme de fidélité.

### Demandes supplémentaires

Les fonctionnalités non décrites ci-dessus sont traitées comme des demandes de modification. Le prestataire envoie une estimation sous 2 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

### Exigences obligatoires

- Au maximum 15 réservations par séance.
- La page d'accueil atteint un Largest Contentful Paint inférieur à 2,5 secondes sur une connexion 4G simulée.
- La base de données est sauvegardée chaque jour et les sauvegardes sont conservées 30 jours.
- Les mots de passe sont hachés avec Argon2id.

### Jalons et paiements

- M1, à livrer à la fin de la semaine 5 : prototype cliquable et modèle de données. Paiement : 10 % du prix.
- M2, à livrer à la fin de la semaine 6 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 40 % du prix.
- M3, à livrer à la fin de la semaine 10 : back-office, notifications et rapport de tests. Paiement : 30 % du prix.
- M4, à livrer à la fin de la semaine 17 : mise en production et documentation de passation. Paiement : 20 % du prix.

### Validation des jalons

Le client dispose de 7 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 1 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

### Conditions contractuelles

Prix forfaitaire : 40 500 TND hors TVA, payé par jalon. Les factures sont payables sous 45 jours.

La propriété intellectuelle de l'application livrée est transférée au client après le paiement final. Garantie : le prestataire corrige sans frais les défauts signalés dans les 60 jours suivant la réception finale. Résiliation : chaque partie peut résilier avec un préavis écrit de 30 jours.

Les parties gardent les informations confidentielles pendant 3 ans après la fin du projet.

### Gouvernance du projet

Un point d'avancement de 30 minutes a lieu chaque lundi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

