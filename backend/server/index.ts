import express from "express";
import cors from "cors";
import bodyParser from "body-parser";

import { router as priceSchedulerRoutes } from "./routes/price-scheduler"
// import other routers here

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(bodyParser.json());

app.use("/api/price-scheduler", priceSchedulerRoutes);
// app.use("/api/product-creator", productCreatorRoutes);

app.get("/api/health", (req, res) => {
  res.send("✅ Backend server is up!");
});

app.listen(PORT, () => {
  console.log(`🚀 Server running at http://localhost:${PORT}`);
});
