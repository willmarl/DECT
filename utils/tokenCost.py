def calculate_cost(response, model="gpt-4o-mini"):
    """
    Calculate the cost of an OpenAI chat completion response in USD.
    
    Args:
        response: The API response object from client.chat.completions.create(...)
        model (str): The model name (default: gpt-4o-mini)
        
    Returns:
        float: The total cost in USD
    """
    # Pricing table (per token, USD)
    pricing = {
        "gpt-4o-mini": {
            "input": 0.00000015,
            "output": 0.00000060
        },
        "gpt-4o": {
            "input": 0.00000250,
            "output": 0.00001000
        }
        # add more models if you use them
    }
    
    if model not in pricing:
        raise ValueError(f"Model {model} not in pricing table.")
    
    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens
    
    input_cost = prompt_tokens * pricing[model]["input"]
    output_cost = completion_tokens * pricing[model]["output"]
    total_cost = input_cost + output_cost
    
    return total_cost
