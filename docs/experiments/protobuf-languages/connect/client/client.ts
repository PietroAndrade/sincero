/**
 * The front-end's side of the round trip: a generated, typed client calling the Python Connect
 * server — over the Connect protocol (JSON and binary) and over gRPC-Web, the two protocols a
 * browser can speak (`@connectrpc/connect-web` uses the same transports on `fetch`).
 *
 *     npm install && npm start          (with the server running on :8765)
 */
import { createClient, ConnectError, Code } from "@connectrpc/connect";
import { createConnectTransport, createGrpcWebTransport } from "@connectrpc/connect-node";
import { create } from "@bufbuild/protobuf";
import { Simulations } from "./gen/sincero/api_pb.js";
import { SimulationInputSchema } from "./gen/sincero/simulation_input_pb.js";

const baseUrl = "http://127.0.0.1:8765";
const transports = {
  "connect+json": createConnectTransport({ baseUrl, httpVersion: "1.1", useBinaryFormat: false }),
  "connect+proto": createConnectTransport({ baseUrl, httpVersion: "1.1", useBinaryFormat: true }),
  "grpc-web": createGrpcWebTransport({ baseUrl, httpVersion: "1.1" }),
};

const ra = create(SimulationInputSchema, { name: "RA", listPrice: 440000, monthsRemaining: 19, fgtsUpfront: 13000,
                                           developerInstallment: 2500, balloonMonths: [6, 12] });

for (const [name, transport] of Object.entries(transports)) {
  const client = createClient(Simulations, transport);
  const { id } = await client.createSimulation(ra);                                   // typed request, typed response
  const resource = await client.getSimulation({ id });
  const node = await client.getNode({ id, path: "mortgage", fields: ["hidden_incc_debt"] });
  console.log(`# ${name}`);
  console.log(`  created ${id}; summary.total_cost = ${resource.summary?.totalCost}; input echoed: ${resource.input?.name}, ${resource.input?.balloonMonths}`);
  console.log(`  GET mortgage?fields=hidden_incc_debt -> ${new TextDecoder().decode(node.json)}`);
  try {
    await client.createSimulation(create(SimulationInputSchema, { listPrice: 440000, monthsRemaining: 0 }));
  } catch (e) {
    const err = ConnectError.from(e);
    console.log(`  months_remaining 0 -> ${Code[err.code]}: ${err.rawMessage}`);                 // the model's 422 text, verbatim
  }
  try {
    await client.getSimulation({ id: "deadbeef" });
  } catch (e) {
    console.log(`  unknown id -> ${Code[ConnectError.from(e).code]}`);
  }
}
