import streamlit as st
from google import genai
from google.genai import types

def calculate_discount(price: float, discount_percent: float) -> str:
    discount_amount = price * (discount_percent / 100.0)
    final_price = price - discount_amount
    return f"Початкова ціна: {price} грн. Знижка {discount_percent}% складає {discount_amount} грн. Фінальна вартість товару: {final_price} грн."

st.set_page_config(page_title="AI-агент Знижок", page_icon="🛍️")
st.title("🛍️ AI-агент: Шопінг-помічник")

api_key_input = st.text_input("Введіть свій Google Gemini API Key:", type="password")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_prompt := st.chat_input("Наприклад: Скільки коштуватиме куртка за 2400 грн зі знижкою 15%?"):
    if not api_key_input:
        st.error("Будь ласка, вкажіть API ключ у полі вище.")
        st.stop()

    clean_api_key = api_key_input.strip()

    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    try:
        client = genai.Client(api_key=clean_api_key)

        config = types.GenerateContentConfig(
            tools=[calculate_discount],
            temperature=0,
        )

        history_contents = []
        for msg in st.session_state.messages:
            history_contents.append(
                types.Content(
                    role=msg["role"],
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )

        with st.chat_message("assistant"):
            with st.spinner("Агент аналізує запит..."):
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=history_contents,
                    config=config
                )

                if response.function_calls:
                    for call in response.function_calls:
                        if call.name == "calculate_discount":
                            args = call.args
                            st.info(f"⚙️ **Виклик `calculate_discount`**: `price`={args['price']}, `discount_percent`={args['discount_percent']}")
                            
                            fn_result = calculate_discount(
                                price=float(args['price']), 
                                discount_percent=float(args['discount_percent'])
                            )

                            followup_response = client.models.generate_content(
                                model='gemini-2.0-flash',
                                contents=[
                                    types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
                                    types.Content(role="model", parts=[types.Part.from_function_call(name=call.name, args=call.args)]),
                                    types.Content(role="user", parts=[
                                        types.Part.from_function_response(
                                            name=call.name,
                                            response={"result": fn_result}
                                        )
                                    ])
                                ]
                            )
                            final_text = followup_response.text
                else:
                    final_text = response.text

                st.markdown(final_text)
                st.session_state.messages.append({"role": "assistant", "content": final_text})

    except Exception as e:
        st.error(f"Помилка виконання запиту: {e}")
