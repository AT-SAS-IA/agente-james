import urllib.request
import json

def call_chat(question, history):
    url = "http://127.0.0.1:8000/chat"
    data = json.dumps({
        "question": question,
        "history": history
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body)
    except Exception as e:
        print(f"Error calling /chat: {e}")
        return None

def main():
    print("=== STARTING MULTI-TURN TEST ===")
    
    # Turn 1
    q1 = "Que heladeras tenes"
    print(f"\nUser: {q1}")
    res1 = call_chat(q1, [])
    if not res1:
        return
        
    print(f"Assistant:\n{res1['answer']}")
    print(f"Sources: {res1['sources']}")
    
    # Turn 2
    q2 = "Mas chico"
    print(f"\nUser: {q2}")
    history = [
        {"role": "user", "content": q1},
        {"role": "assistant", "content": res1["answer"]}
    ]
    res2 = call_chat(q2, history)
    if not res2:
        return
        
    print(f"Assistant:\n{res2['answer']}")
    print(f"Sources: {res2['sources']}")

if __name__ == "__main__":
    main()
