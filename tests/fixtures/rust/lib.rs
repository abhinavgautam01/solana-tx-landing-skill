use anchor_lang::prelude::*;
use solana_program::program::invoke_signed;

pub fn settle_many(ctx: Context<SettleMany>, count: u64) -> Result<()> {
    for _ in 0..count {
        msg!("settling");
        invoke_signed(
            &ctx.accounts.some_ix,
            &[],
            &[&[b"vault", &[ctx.bumps.vault]]],
        )?;
    }
    Ok(())
}

#[derive(Accounts)]
pub struct SettleMany<'info> {
    /// CHECK: fixture only
    pub vault: AccountInfo<'info>,
    /// CHECK: fixture only
    pub some_ix: AccountInfo<'info>,
}

