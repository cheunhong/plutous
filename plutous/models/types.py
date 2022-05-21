from pydantic import condecimal


Amount = condecimal(max_digits=20, decimal_places=8)
