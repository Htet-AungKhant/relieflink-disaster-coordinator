use relieflink_db;

// -----------------------------------------------------------------------------
// STEP 1: CLEANUP EXISTING COLLECTIONS
// -----------------------------------------------------------------------------
db.relief_camps.drop();
db.relief_requests.drop();
db.donors_ngos.drop();

print(">>> Dropped existing collections.");

// -----------------------------------------------------------------------------
// STEP 2: SCHEMA VALIDATION RULES ($jsonSchema)
// -----------------------------------------------------------------------------

// Collection 1: relief_camps
db.createCollection("relief_camps", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["camp_name", "zone", "population", "contact_person", "location", "supplies_inventory"],
      properties: {
        camp_name: { bsonType: "string" },
        zone: { bsonType: "string" },
        population: { bsonType: "int", minimum: 0 },
        contact_person: {
          bsonType: "object",
          required: ["name", "phone"],
          properties: {
            name: { bsonType: "string" },
            phone: { bsonType: "string" }
          }
        },
        location: {
          bsonType: "object",
          required: ["type", "coordinates"],
          properties: {
            type: { bsonType: "string" },
            coordinates: { bsonType: "array", minItems: 2, maxItems: 2 }
          }
        },
        supplies_inventory: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["item_name", "category", "quantity", "unit"],
            properties: {
              item_name: { bsonType: "string" },
              category: { bsonType: "string" },
              quantity: { bsonType: "int", minimum: 0 },
              unit: { bsonType: "string" }
            }
          }
        }
      }
    }
  }
});

// Collection 2: relief_requests
db.createCollection("relief_requests", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["camp_id", "requested_items", "urgency_level", "status", "requested_at"],
      properties: {
        camp_id: { bsonType: "objectId" },
        requested_items: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["item_name", "category", "required_quantity", "unit"],
            properties: {
              item_name: { bsonType: "string" },
              category: { bsonType: "string" },
              required_quantity: { bsonType: "int", minimum: 1 },
              unit: { bsonType: "string" }
            }
          }
        },
        urgency_level: { enum: ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
        status: { enum: ["PENDING", "IN_TRANSIT", "FULFILLED"] },
        requested_at: { bsonType: "date" }
      }
    }
  }
});

// Collection 3: donors_ngos
db.createCollection("donors_ngos", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["ngo_name", "supported_zones", "contact_email"],
      properties: {
        ngo_name: { bsonType: "string" },
        supported_zones: { bsonType: "array", items: { bsonType: "string" } },
        contact_email: { bsonType: "string" }
      }
    }
  }
});

print(">>> Schema Validation Rules Enforced Successfully.");

// -----------------------------------------------------------------------------
// STEP 3: SEEDING DATA (100 CAMPS & 2,000 REQUESTS)
// -----------------------------------------------------------------------------

// Insert 100 Relief Camps
const zones = ["North-District", "South-District", "East-District", "West-District", "Central-District"];
const camps = [];

for (let i = 1; i <= 100; i++) {
  camps.push({
    camp_name: `Relief Camp ${i}`,
    zone: zones[i % zones.length],
    population: NumberInt(Math.floor(Math.random() * 1000) + 100),
    contact_person: { name: `Leader ${i}`, phone: `+959700000${i}` },
    location: { type: "Point", coordinates: [96.15 + (i * 0.001), 16.85 + (i * 0.001)] },
    supplies_inventory: [
      { item_name: "Drinking Water (Liters)", category: "Water", quantity: NumberInt(Math.floor(Math.random() * 2000) + 100), unit: "Liters" },
      { item_name: "Emergency Food Pack", category: "Food", quantity: NumberInt(Math.floor(Math.random() * 500) + 50), unit: "Packs" }
    ],
    created_at: new Date()
  });
}

const campRes = db.relief_camps.insertMany(camps);
const campIds = Object.values(campRes.insertedIds);

print(`>>> Inserted ${campIds.length} Relief Camps.`);

// Insert 2,000 Relief Requests
const requests = [];
const urgencyLevels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const statuses = ["PENDING", "IN_TRANSIT", "FULFILLED"];

for (let i = 1; i <= 2000; i++) {
  requests.push({
    camp_id: campIds[i % campIds.length],
    requested_items: [
      { item_name: "Drinking Water (Liters)", category: "Water", required_quantity: NumberInt(Math.floor(Math.random() * 300) + 20), unit: "Liters" }
    ],
    urgency_level: urgencyLevels[i % 4],
    status: statuses[i % 3],
    requested_at: new Date(Date.now() - Math.floor(Math.random() * 100) * 86400000)
  });
}

db.relief_requests.insertMany(requests);
print(">>> Inserted 2,000 Relief Requests.");

// Insert Donors & NGOs
db.donors_ngos.insertMany([
  {
    ngo_name: "Global Disaster Response Network",
    supported_zones: ["North-District", "South-District", "Central-District"],
    contact_email: "support@gdrn.org"
  },
  {
    ngo_name: "Red Cross Emergency Initiative",
    supported_zones: ["East-District", "West-District"],
    contact_email: "info@redcross-initiative.org"
  }
]);

print(">>> Seeded Donors and NGOs.");

// -----------------------------------------------------------------------------
// STEP 4: INDEXING STRATEGIES
// -----------------------------------------------------------------------------

db.relief_camps.createIndex({ zone: 1 });
db.relief_camps.createIndex({ camp_name: "text" });
db.relief_requests.createIndex({ status: 1, urgency_level: 1 });

print(">>> Single, Text, and Compound Indexes Created Successfully.");

// -----------------------------------------------------------------------------
// STEP 5: AGGREGATION PIPELINES
// -----------------------------------------------------------------------------

// Pipeline 1: Critical Requests Grouped by Geographic Zone
const criticalDemandsByZone = db.relief_requests.aggregate([
  { $match: { urgency_level: "CRITICAL", status: "PENDING" } },
  {
    $lookup: {
      from: "relief_camps",
      localField: "camp_id",
      foreignField: "_id",
      as: "camp_details"
    }
  },
  { $unwind: "$camp_details" },
  {
    $group: {
      _id: "$camp_details.zone",
      total_critical_requests: { $sum: 1 } } }, {$sort: { total_critical_requests: -1 } }
]).toArray();

print("\n--- AGGREGATION: CRITICAL PENDING REQUESTS BY ZONE ---");
printjson(criticalDemandsByZone);

// Pipeline 2: Low Inventory Warning per Camp (< 300 units)
const lowSupplyAlerts = db.relief_camps.aggregate([
  { $unwind: "$supplies_inventory" },
  { $match: { "supplies_inventory.quantity": { $lt: 300 } } }, {$project: {
      _id: 0,
      camp_name: 1,
      zone: 1,
      item_name: "$supplies_inventory.item_name",
      remaining_quantity: "$supplies_inventory.quantity",
      unit: "$supplies_inventory.unit"
    }
  }]).toArray();