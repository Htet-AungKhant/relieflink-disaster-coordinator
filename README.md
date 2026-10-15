# ReliefLink: Smart Disaster Relief Coordinator

ReliefLink is a NoSQL database application designed to streamline disaster relief management, emergency supply allocation, and demand forecasting. Built using MongoDB and PyMongo, this system aligns with UN Sustainable Development Goals (SDG 1: No Poverty and SDG 11: Sustainable Cities and Communities).

## Repository Structure

- `database_creation_and_indexing.js`: MongoDB shell script handling collection initialization, `$jsonSchema` validation rules, data seeding (100 camps and 2,000 requests), indexing strategies, and aggregation pipelines.
- `predictive_analytics_and_query_optimization.ipynb`: Jupyter Notebook covering PyMongo CRUD operations, a Random Forest regression model for supply demand forecasting, and an automated query execution analyzer using `explain()`.

## Tech Stack

- Database: MongoDB 7.0+, `mongosh`
- Programming Language: Python 3.x
- Libraries: PyMongo, Pandas, Scikit-Learn, Seaborn, Matplotlib
- Environment: Jupyter Lab

## Core Features & Database Design

1. Schema Validation: Enforced document integrity at the collection level using `$jsonSchema` rules.
2. Data Modeling: Hybrid approach combining embedded subdocuments (contact details, geospatial coordinates, inventory arrays) and referenced relationships (`camp_id` foreign keys).
3. Indexing & Optimization: Single-field, text, and compound indexes implemented to replace full collection scans (`COLLSCAN`) with index scans (`IXSCAN`).
4. Aggregation Pipelines: Multi-stage data processing (`$match`, `$lookup`, `$unwind`, `$group`, `$sort`) for critical demand analysis and inventory warnings.
5. Demand Forecasting: Machine learning workflow extracting historical camp metrics to train a `RandomForestRegressor` for forecasting required resource quantities.
6. Dynamic Query Tuning: Custom Python engine inspecting MongoDB `explain()` execution stats to identify unindexed queries and auto-generate compound indexes.

## How to Run

1. Initialize Database & Seed Data:
   Execute the JavaScript script inside `mongosh`:
   ```bash
   mongosh "mongodb://localhost:27017" database_creation_and_indexing.js
