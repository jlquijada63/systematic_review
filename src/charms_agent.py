
from os import name

from agents import Agent, Runner

from prompts import CHARMS_PF_INSTRUCTIONS

from models import CharmsPfRecord

import asyncio

from helpers import extract_pdf_text_and_tables_markdown

from dotenv import load_dotenv

load_dotenv()




charms_pf_agent = Agent(
  name='Charm_pf Agent',
  model='gpt-5-mini',
  instructions=CHARMS_PF_INSTRUCTIONS,
  output_type=CharmsPfRecord
  
)

article_converted = extract_pdf_text_and_tables_markdown(pdf_path='./documents/hip_fracture_prognosis.pdf')

async def main():
  
  result = await Runner.run(charms_pf_agent,input= f"analiza el siguiente articulo: {article_converted}")
  print(result.final_output)
  
  
if __name__ == "__main__":
  
  asyncio.run(main())
  
  
