# Understanding the COT Strength Engine: Analyzing Forex Market Sentiment with Python

## Abstract
The Commitments of Traders (COT) report, issued weekly by the U.S. Commodity Futures Trading Commission (CFTC), provides critical insights into forex market sentiment by detailing the positions of various trader groups. This article examines two Python scripts, `cot_collector.py` and `cot_strength_engine.py`, which automate the collection, processing, and analysis of COT data to generate trading recommendations. By calculating a sentiment-based strength score and deriving trading signals for major currency pairs, these scripts offer traders a data-driven approach to decision-making. This article outlines their functionalities, practical applications, limitations, and potential enhancements, making them valuable tools for forex traders and developers.

## Introduction
The Commitments of Traders (COT) report, published weekly by the U.S. Commodity Futures Trading Commission (CFTC), is a powerful tool for forex traders seeking insights into market sentiment. By analyzing the positions of various market participants—non-commercial traders (such as hedge funds), commercial traders, and non-reportable traders—the COT report provides a snapshot of market dynamics. The provided Python scripts, `cot_collector.py` and `cot_strength_engine.py`, offer a robust framework for collecting, processing, and analyzing COT data to generate actionable trading recommendations. This article explores how these scripts work, their key functionalities, and their value for forex trading strategies.

## Collecting COT Data with `cot_collector.py`

The first script, `cot_collector.py`, is designed to scrape and parse COT data from the CFTC website, specifically from the Chicago Mercantile Exchange (CME) futures reports. Here's how it operates:

### Key Functionalities
1. **Data Retrieval**: The script fetches the latest COT report from the CFTC's URL (`https://www.cftc.gov/dea/futures/deacmesf.htm`) or an alternative user-provided URL for historical data. It uses the `requests` library to download the HTML content and `BeautifulSoup` to extract the relevant `<pre>` tag containing the raw COT data.

2. **Data Parsing**: The script processes the raw text using regular expressions to identify and extract key metrics for each instrument (e.g., Euro FX, Japanese Yen). These metrics include:
   - **Open Interest**: The total number of outstanding contracts.
   - **Commitments**: Positions held by non-commercial, commercial, and non-reportable traders, including long, short, and spread positions.
   - **Percentages**: The proportion of open interest attributed to each trader category.
   - **Trader Count**: The number of traders in each category.
   - **Date**: The report's issuance date, formatted as `YYYY-MM-DD`.

3. **Data Storage**: Parsed data is saved in two JSON files:
   - `cot.json`: Stores the most recent report data, organized by date and instrument.
   - `cot_history.json`: Maintains a historical record of all collected data, preventing duplicates by checking dates.

4. **Update Management**: The script tracks the last update date in `last_updated/cot.txt` to avoid redundant downloads on the same day, ensuring efficiency.

### Workflow
- The script starts by ensuring the necessary directories exist (`data` and `last_updated`).
- It checks if the COT data was already updated today. If not, it downloads the latest report.
- The raw text is parsed into a structured format, with each instrument's data stored as a dictionary containing its metrics.
- The parsed data is merged into the historical record and saved to the output files.
- Console messages confirm the process, including any errors during parsing (e.g., malformed data).

This script provides a reliable pipeline for collecting and storing COT data, forming the foundation for further analysis.

## Analyzing COT Data with `cot_strength_engine.py`

The `cot_strength_engine.py` script takes the collected COT data and transforms it into actionable trading insights. It calculates a "strength score" for major currencies and generates trading recommendations for forex pairs. Here's a breakdown of its functionality:

### Key Functionalities
1. **Currency Mapping**: The script maps CME instrument names (e.g., "EURO FX") to standard currency codes (e.g., "EUR") for seven major currencies: CAD, CHF, GBP, JPY, EUR, NZD, and AUD.

2. **Bias Calculation**: For each instrument, the script computes a **bias** using the formula:
   \[
   \text{Bias} = \frac{\text{Non-commercial Long} - \text{Non-commercial Short}}{\text{Non-commercial Long} + \text{Non-commercial Short}}
   \]
   This measures the net positioning of speculative traders (non-commercial), where a positive bias indicates bullish sentiment and a negative bias indicates bearish sentiment.

3. **Trend and Open Interest Analysis**:
   - **Bias Trend**: The script calculates the percentage change in bias over a specified number of weeks (default: 3) to assess momentum.
   - **Open Interest Change**: It computes the percentage change in open interest over the same period, reflecting market participation.
   - Both metrics are normalized to a range of [-1, 1] to ensure comparability.

4. **Strength Score**: For each currency, a composite score is calculated as:
   \[
   \text{Score} = \text{Normalized Bias} + \text{Normalized Bias Trend} + \text{Normalized Open Interest Change}
   \]
   A score above 0.1 suggests a "BUY" signal, below -0.1 suggests a "SELL" signal, and values in between indicate a "neutral" stance.

5. **USD Score Calculation**: Since the USD is not directly reported as an instrument, its score is derived by averaging the inverse biases of the other seven currencies. For example, if EUR, GBP, and JPY are bearish against USD, the USD bias is positive, reflecting strength.

6. **Trading Recommendations**: The script generates recommendations for 21 major forex pairs (e.g., EURUSD, GBPJPY) by comparing the biases of the base and quote currencies. For a pair like EURUSD, if EUR's bias exceeds USD's, the recommendation is "BUY"; if lower, it's "SELL"; if equal, it's "neutral."

7. **Output**: The results are saved in `cot_strength.json`, including:
   - Bias, trend, and open interest change for each currency.
   - The composite score and direction (BUY/SELL/neutral).
   - The most recent report date.
   - USD-specific metrics, including the number of currencies used in its calculation.
   - Trading recommendations for each forex pair.

### Workflow
- The script loads the COT data from `cot.json`.
- It processes each instrument's data over the specified weeks, calculating bias, trend, and open interest changes.
- The USD score is computed separately based on the inverse biases of other currencies.
- Recommendations are generated by comparing currency biases for valid forex pairs.
- Results are saved to `cot_strength.json`, and key insights (e.g., USD score, recommendations) are printed to the console.

## Practical Applications for Forex Traders

The combined functionality of these scripts offers several benefits for forex traders:

1. **Sentiment Analysis**: The bias metric reflects speculative sentiment, helping traders gauge whether large players are bullish or bearish on a currency. For example, a strong positive bias for EUR suggests hedge funds are heavily long, indicating potential upward pressure on EURUSD.

2. **Trend Confirmation**: The bias trend and open interest change provide context for whether sentiment is strengthening or weakening. A rising bias alongside increasing open interest may signal a robust trend, while a declining bias could indicate fading momentum.

3. **Pair Selection**: The trading recommendations simplify decision-making by identifying pairs with the strongest relative bias differentials. For instance, a "BUY EURUSD" recommendation arises when EUR's bias significantly exceeds USD's, highlighting opportunities for directional trades.

4. **USD Strength Assessment**: The USD score offers a unique perspective on the dollar's relative strength against a basket of major currencies, useful for trading USD-based pairs or assessing broader market trends.

## Example Output
Suppose the most recent COT report is dated June 3, 2025. The `cot_strength_engine.py` script might produce output like:

```
✅ Termômetro de força salvo em: ../oraculum/src/app/data/cot/cot_strength.json

💵 USD Score: 0.3421 (Direction: BUY)
Based on 7 currencies
Most recent COT report date: 2025-06-03

🏆 Recomendações por par:
EURUSD: SELL (0.1234 vs 0.3421)
GBPUSD: NEUTRAL (0.2987 vs 0.3421)
USDJPY: BUY (-0.4567 vs 0.3421)
...
```

This indicates USD strength (positive score), a bearish outlook for EURUSD (EUR weaker than USD), and a bullish outlook for USDJPY (USD stronger than JPY).

## Limitations and Considerations
- **Data Dependency**: The scripts rely on accurate COT data from the CFTC. Any changes to the website's structure could break `cot_collector.py`'s parsing logic.
- **Lagging Indicator**: COT data is released weekly and reflects positions as of the previous Tuesday, so it may lag real-time market developments.
- **Simplification**: The strength score simplifies complex market dynamics. Traders should combine COT analysis with other indicators (e.g., technical or fundamental analysis) for robust decision-making.
- **USD Approximation**: The USD score assumes equal weighting of other currencies, which may not fully capture market nuances.

## Conclusion
The `cot_collector.py` and `cot_strength_engine.py` scripts provide a powerful, automated framework for leveraging COT data in forex trading. By collecting raw data, calculating sentiment-based metrics, and generating trading recommendations, these tools empower traders to make data-driven decisions. Whether you're a seasoned trader or a developer interested in market analysis, these scripts offer a practical starting point for building a sentiment-based trading strategy. To enhance their utility, consider integrating real-time price data or additional technical indicators, and always validate signals with broader market context.

## References
- Commodity Futures Trading Commission. (2025). *Commitments of Traders (COT) Reports*. Retrieved from [https://www.cftc.gov](https://www.cftc.gov).

**Rafael Goulart Pedroso**  
Security researcher & AI developer  
📧 forex@codeartisan.cloud  
📱 [WhatsApp](https://wa.me/5511934251920)
