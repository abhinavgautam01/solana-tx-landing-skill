import {
  appendTransactionMessageInstruction,
  createSolanaRpc,
  createTransactionMessage,
  getSetComputeUnitLimitInstruction,
  getSetComputeUnitPriceInstruction,
  pipe,
  setTransactionMessageFeePayerSigner,
  setTransactionMessageLifetimeUsingBlockhash,
  signTransactionMessageWithSigners,
} from "@solana/kit";

export async function payWithKit(rpcUrl: string, feePayer: any, appInstruction: any) {
  const rpc = createSolanaRpc(rpcUrl);
  const latest = await rpc.getLatestBlockhash({ commitment: "confirmed" }).send();

  const message = pipe(
    createTransactionMessage({ version: 0 }),
    (tx) => setTransactionMessageFeePayerSigner(feePayer, tx),
    (tx) => setTransactionMessageLifetimeUsingBlockhash(latest.value, tx),
    (tx) => appendTransactionMessageInstruction(getSetComputeUnitLimitInstruction({ units: 250_000 }), tx),
    (tx) => appendTransactionMessageInstruction(getSetComputeUnitPriceInstruction({ microLamports: 10_000 }), tx),
    (tx) => appendTransactionMessageInstruction(appInstruction, tx),
  );

  const signed = await signTransactionMessageWithSigners(message);
  const signature = await rpc.sendTransaction(signed, {
    encoding: "base64",
    preflightCommitment: "confirmed",
  }).send();

  return rpc.confirmTransaction({
    signature,
    blockhash: latest.value.blockhash,
    lastValidBlockHeight: latest.value.lastValidBlockHeight,
  }).send();
}
