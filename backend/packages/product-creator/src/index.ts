import { ShopifyClient } from "@shared/utils/ShopifyClient";

const client = new ShopifyClient();

async function main() {
  const customer = await client.getCustomerByEmail("jdazz87@gmail.com");
  console.log("Found customer:", customer);

//   const productRes = await client.createProduct({
//     title: "Test Product",
//     status: "ACTIVE",
//   });

//   console.log("Created product:", productRes);
}

main();