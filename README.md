# trajectoire-pyro

## Objectif général

L'objectif de ce projet est double :

- démontrer l'utilité de PyRo et des stats bayésiennes pour modéliser des carrières
- tester le développement assisté par IA

## Étapes de la création d'un modèle

1. création d'un jeu de données synthétiques (rôle "générateur") ; seule une partie "observable" est communiquée au modélisateur ou au prévisionniste ; les données complètes sont communiqués à l'évaluateur ; les paramètres de génération ne sont communiqués qu'à l'évaluateur
2. l' "auditeur" vérifie que le code écrit par le générateur contient uniquement l'architecture, et que les paramètres sont bien masqués
3. utilisation de Pyro pour développer un estimateur en miroir de la production des données ; le modélisateur connaît l'architecture de la génération des données (= le code) mais EN AUCUN CAS la valeur des paramètres (= le fichier de configuration) (rôle "modélisateur")
4. comparaison des résultats de l'estimation avec les paramètres du modèle de génération (rôle "évaluateur")
5. à partir du modèle estimé, prolongation des carrières et création de nouvelles carrières (rôle "prévisionniste")
6. comparaison avec les données synthétiques, en prenant compte de toutes les sources d'incertitude (rôle "évaluateur")
7. l'évaluateur veille également à mesurer le temps d'exécution et l'espace mémoire utilisé par le modélisateur
8. l'auditeur fait un retour critique sur l'ensemble des étapes précédentes, fait des propositions d'amélioration d'application directe ou à développer dans le futur

## Contraintes

- exécution dans un environnement isolé (conteneur)
- utilisation de `uv` comme gestionnaire d'environnement
- écriture de tests unitaires
- les données, paramètres, estimations, évaluations, etc. sont convenablement organisés selon une architecture de fichier bien pensée (rôle "planificateur")
- la comparaison elle-même des modèles est planifiée, documentée puis progressivement enrichie (rôle "planificateur")
- la documentation globale est planifiée puis progressivement enrichie (rôle "documentaliste")
- les paramètres des modèles générateurs des données sont stockés dans un fichier de config, qui n'est pas accessible au modélisateur, mais qui l'est pour l'évaluateur ; cela permet de communiquer le code du générateur au modélisateur, mais sans communiquer les paramères
- chaque avancée doit être documentée dans news.md et consolidée dans la documentation
- dans la documentation, des tableaux de synthèses doivent comparer les approches et la qualité des modèles (rôle "documentaliste")
- dans la documentation, un graphe doit expliquer par des flèches quels modèles sont des cas particuliers d'un modèle plus complexe (rôle "documentaliste")

## Fonctionalités

- [ ] Comparaison des donnés synthétiques et resimulées selon : nombre de personne en activité par année ; volume de revenu versé par année ; distribution des revenus par type d'emploi, par âge et par année ; nombre de pensionnés par année ; volume des pensions versées par année ; distribution des pensions. Il n'est pas fondamental qu'une carrière soit cohérente entre les données synthétiques et les données resimulées, tant que l'ensemble des carrière reste cohérent en nombre d'invidus dans chaque état, en volumes monétaires et en distributions
- [ ] Pour chaque évaluation, utiliser plusieurs config et non pas une seule, afin de mieux vérifier la convergence des estimateurs
- [ ] Pour chaque évaluation, faire varier la taille de l'échantillon et regarder les critères d'évaluation "en convergence quand n devient grand"
- [ ] Modélisation d'un modèle simple à quatre états (inactivité / emploi / retraite / mort), puis 5, 6, 7, 8... en augmentant les types d'emplois (privé, public, etc.) et d'inactivité (enfance, études, chômage, maternité, maladie, invalidité, etc.)
- [ ] Représentation de l'incertitude autour des quantités agrégées (intervalle de crédibilité) : nombre de personne, volumes monétaires, revenu moyen, etc.
- [ ] Représentation de l'incertitude autour des distributions : distribution des pensions, distribution des salaires
- [ ] Utilisation ou non de covariables fixes (âge, année de naissance, lieu de naissance, catégorie sociale des parents, etc.)
- [ ] Utilisation de variables latentes à 1, 2, 3, ... dimensions, contrôlant les idiosynchrasies de chaque individu (sa propension à obtenir un bon salaire, à rester dans un type d'activité, à partir tôt à la retraite, etc.)
- [ ] Modélisation du revenu comme une variable complémentaire à l'état `emploi` ou comme au contraire comme un vecteur de revenus (`r_{cnav,t}=1200`, `r_{sre,t}=200`, `r_{msa,t}=0`) au lieu d'états discret
- [ ] Modélisation de la pension comme une variable complémentaire à l'état `retraite` selon des règles déterministes (revenu des 20 meilleures années / 2 puis revalorisation annuelle constante de 3%) ; les règles déterministes peuvent être partagées entre la personne qui synthétise les données et la personne qui effectue la modélisation, au même titre que l'architecture du modèele, mais à la différence des paramètres
- [ ] Complexifier la dépendance des variables aux variables latentes (non linéarités via diverses architectures neurales) + utiliser de l'inférence amortie
- [ ] Modélisation de la quotité de travail (avec pics à 50% et 80%)
- [ ] Implémenter une façon de modéliser des hypothèses du type : "le taux de chômage augmente jusqu'en 2040 puis reste constante", "l'âge moyen d'entrée sur le marché du travail est fixée à 18 ans", etc.
- [ ] Intégration de données macroéconomiques sérielles (chroniques du nombre de cotisants dans tel régime) ou ponctuelles (espérance de vie en année x)
- [ ] Co-génération d'un échantillon représentatif des données de cadrage macroéconomique (i.e. n << N trajectoires diverses dont l'agrégation s'approche des vraies données)
- [ ] Présence ou non d'un âge d'ouverture des droits à la retraite, variant de façon déterministe avec l'année de naissance
- [ ] Simulation des carrières est "par couche" : simuler d'abord les dates de naissance et de mort, puis dans un deuxième temps on simuler des carrières conditionnellement à ces dates
- [ ] Génération de carrières _differentially-private_
- [ ] Enrichir la comparaison des paramètres estimés et vrais (ex: différentes mesures du degré d'adéquation ? convergence lorsque le nombre d'exemples augmente ?)
- [ ] Enrichir la mesure de qualité des carrière simulées
- [ ] Données soit complètement observable (un individu de sa naissance à sa mort), soit avec des schémas d'enquête plus complexe (carrière des individus observables de la naissance à l'année d'enquête)
- [ ] Est-ce qu'un modèles d'estimation avancé retrouve les paramètres d'un modèle plus simple (qui en est un cas particulier) ?

## Points de vigilences

- Est-ce que l'estimation est numériquement identifiée ? Causalement ?
- Est-ce que la mortalité est susceptible de perturber l'estimation ? (possible biais de sélection)
