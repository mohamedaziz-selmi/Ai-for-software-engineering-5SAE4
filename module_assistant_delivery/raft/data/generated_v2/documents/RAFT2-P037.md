# Note de cadrage - Studio Atlas Fitness

Document d'entraînement synthétique RAFT2-P037. Le client, les personnes et les chiffres sont fictifs.

## 1. Présentation du projet

Aujourd'hui, Studio Atlas Fitness gère ses réservations avec des tableurs et des appels téléphoniques. Ce projet livre une application web de réservation de cours.

## 2. Parties

Le client est Studio Atlas Fitness. L'adresse de contact projet du client est pm.raft2p037@example.com ; les urgences peuvent être signalées au +216 76 261 410. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre fonctionnel

| Fonctionnalité | Statut |
|---|---|
| Recevoir un e-mail de rappel 24 heures avant un cours | Inclus |
| La livraison à domicile | Exclu |
| Permettre au personnel de créer et modifier les cours | Inclus |
| Permettre aux coachs de consulter la liste des participants | Inclus |
| Un programme de fidélité | Exclu |
| Réserver et annuler un cours | Inclus |
| S'inscrire sur liste d'attente quand un cours est complet | Inclus |
| La tarification multi-devises | Exclu |

## 4. Évolutions du périmètre

Toute fonctionnalité non listée dans le périmètre est une demande de modification. Le prestataire envoie une estimation sous 2 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences obligatoires

- NN-1: La page d'accueil atteint un Largest Contentful Paint inférieur à 3 secondes sur une connexion 4G simulée.
- NN-2: Au maximum 25 réservations par séance.
- NN-3: Les pages destinées aux clients respectent le WCAG 2.2 niveau AA.
- NN-4: Les mots de passe sont hachés avec scrypt.

## 6. Jalons et paiements

| Jalon | Échéance | Livrables | Paiement |
|---|---|---|---|
| M1 | Fin de la semaine 2 | Prototype cliquable et modèle de données | 20% |
| M2 | Fin de la semaine 3 | Parcours utilisateur principal fonctionnel en préproduction | 30% |
| M3 | Fin de la semaine 9 | Back-office, notifications et rapport de tests | 30% |
| M4 | Fin de la semaine 17 | Mise en production et documentation de passation | 20% |

## 7. Recette

Le client dispose de 10 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 1 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions commerciales

| Clause | Valeur |
|---|---|
| Prix | Prix forfaitaire : 19 500 TND hors TVA |
| Factures | Les factures sont payables sous 30 jours |
| Garantie | Le prestataire corrige sans frais les défauts signalés dans les 60 jours suivant la réception finale |
| Résiliation | Chaque partie peut résilier avec un préavis écrit de 15 jours |
| Propriété intellectuelle | La propriété intellectuelle de l'application livrée est transférée au client après le paiement final |
Les parties gardent les informations confidentielles pendant 1 ans après la fin du projet.

Retard : une pénalité de 0,5 % du prix par semaine de retard s'applique, plafonnée à 10 %.

## 9. Gouvernance du projet

Un point d'avancement de 45 minutes a lieu chaque jeudi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

