export class EconomyService {
  constructor({store,bus}){this.store=store;this.bus=bus;}
  balance(currency='gold'){return Number(this.store.select(s=>s.player?.currencies?.[currency])??0);}
  credit(currency,amount,reason='system'){amount=Number(amount);if(!(amount>0))throw new Error('Positive amount required');this.store.update(s=>{s.player??={};s.player.currencies??={};s.player.currencies[currency]=Number(s.player.currencies[currency]??0)+amount;},{source:'economy:credit',reason});this.bus?.emit('economy:changed',{currency,delta:amount,reason});}
  debit(currency,amount,reason='system'){amount=Number(amount);if(!(amount>0))throw new Error('Positive amount required');if(this.balance(currency)<amount)return false;this.store.update(s=>{s.player.currencies[currency]-=amount;},{source:'economy:debit',reason});this.bus?.emit('economy:changed',{currency,delta:-amount,reason});return true;}
}
