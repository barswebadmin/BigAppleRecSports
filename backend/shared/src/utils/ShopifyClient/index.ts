// shared/src/utils/ShopifyClient/index.ts
import { ShopifyClientCore } from "./core";
import { CREATE_PRODUCT_MUTATION } from "./mutations/createProduct";
import { GET_CUSTOMER_BY_EMAIL } from "./queries/getCustomerByEmail";
import { UPDATE_INVENTORY_QUANTITY } from "./mutations/updateInventory";

export class ShopifyClient extends ShopifyClientCore {
  async createProduct(input: Record<string, unknown>) {
    const res = await this.request(CREATE_PRODUCT_MUTATION, { input });
    return res.data?.productCreate;
  }

  async getCustomerByEmail(email: string) {
    const res = await this.request(GET_CUSTOMER_BY_EMAIL, { email });
    return res.data?.customers?.edges?.[0]?.node ?? null;
  }

  async updateInventory(input: Record<string, unknown>) {
    const res = await this.request(UPDATE_INVENTORY_QUANTITY, { input });
    return res.data?.inventoryAdjustQuantities;
  }
}