### Farm Trace

[![CI](https://github.com/lambda-drama/Farm-Trace/actions/workflows/ci.yml/badge.svg)](https://github.com/lambda-drama/Farm-Trace/actions/workflows/ci.yml)

Farm Trace is the farm-management side of ERPNext. You keep farmers, their farms, their groups and the places they live in Farm Trace, record what you buy from them, and pull the same information in automatically from the KoboToolbox forms your field team fills in.

### What you can do

- Keep a register of **farmers, farms and farmer groups**, and the geography behind them (country to state to district to ward to village).
- Record **purchases from farmers** and turn them into ERPNext Purchase Receipts.
- Pull **farmer, farm and procurement forms** submitted in KoboToolbox straight into Farm Trace.
- Generate **EAN-13 barcodes** for produce transactions.
- Follow volumes, payments and coverage on the **Farm Trace**, **Purchase Dashboard** and **KoboToolbox** workspaces.

### What's in this manual

1. [Set up Farm Trace](#1-set-up-farm-trace)
2. [Set up your master data](#2-set-up-your-master-data)
3. [Record a purchase from a farmer](#3-record-a-purchase-from-a-farmer)
4. [Turn purchases into a Purchase Receipt](#4-turn-purchases-into-a-purchase-receipt)
5. [Barcodes](#5-barcodes)
6. [Pull data in from KoboToolbox](#6-pull-data-in-from-kobotoolbox)
7. [What a sync does to your records](#7-what-a-sync-does-to-your-records)
8. [Workspaces and dashboards](#8-workspaces-and-dashboards)
9. [Troubleshooting](#9-troubleshooting)
10. [Who can do what](#10-who-can-do-what)

### 1. Set up Farm Trace

Farm Trace is an app on a Frappe/ERPNext site, so an administrator installs it once for the whole team:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app farmtrace
```

Then open the site, log in and search for **Farm Trace** in the awesome bar (`Ctrl`/`Cmd` + `K`).

**Who can use it.** Every DocType in Farm Trace grants its rights to the **System Manager** role only. Either give your users System Manager, or create a role for them and grant the rights you want in *Role Permission Manager* (see section 10).

**What the server needs.** The app uses libraries that ship with a normal bench: `requests` (the KoboToolbox API), Pillow (photo rotation) and `python-barcode` (barcode images). If barcode generation reports a missing library, install it into the bench environment (`./env/bin/pip install python-barcode`) and try again.

### 2. Set up your master data

Work from the top of this table down, because each list refers to the ones above it.

| Order | What you create | Why |
| --- | --- | --- |
| 1 | Country, State, District, Ward, Village | The geography everything else hangs from. Country comes from ERPNext; the other four are Farm Trace DocTypes. |
| 2 | Crop | One row per crop, linked to the ERPNext Item you buy it as. |
| 3 | Farmer Group | The group or market centre a farmer delivers to. |
| 4 | Farmer | The person you buy from. |
| 5 | Farm | The plots belonging to a farmer. |
| 6 | Trainings and seasons | Farmer Season, Farmer Training, Farmer Training Method, Farmer Training Status, Farmer Training Topic, Topic Category. |
| 7 | Agents | Field staff and the number sequences they use. |

#### 2.1 Geography: country to state to district to ward to village

Create each level before the one below it, because the levels are linked:

1. **State** – enter the state name and its country.
2. **District** – enter the district and its state; the country follows automatically and stays read-only.
3. **Ward** – enter the ward and its district; state and country follow automatically.
4. **Village** – enter the village, its ward and its district; the rest follows automatically.

Records are named from what you type: a State after the state, a District after the district, and a Village as `village-district`.

#### 2.2 Crops

A Crop is a Farm Trace record with a **crop name** and the **Item** you buy that crop as. The crop is named after its name, and the linked item is used to fill in purchases that arrive from KoboToolbox.

#### 2.3 Farmer groups

A **Farmer Group** is the group or market centre its members deliver to: enter the group name and the village, and district, state and country come from the village. The group is named `group name-district`.

#### 2.4 Farmers

Fill in the farmer's details and save. Worth knowing:

- **Farmer ID** – required, because the record is named after it. Use the reference you already keep for that farmer; the Kobo sync matches on it too, so keep it consistent with your forms.
- **Village** – pick the village and District, State and Country fill in automatically (read-only).
- **Full name** and **Age** are worked out for you from the name parts and the date of birth.
- The address, contact, insurance, loan, identity document and social sections are optional; fill in the ones your programme reports on.
- A **Supplier** is created behind the scenes the first time you make a Purchase Receipt for the farmer, so you do not have to add one by hand.

#### 2.5 Farms

Everything about a plot lives on the **Farm**:

- **Farm ID** – required, because the record is named after it; a farm created by a Kobo sync uses the submission id when the form does not carry one.
- **Farm Name** and **Farmer** are required as well, and **Village** fills in district, state and country for you.
- **Hectares**, land in production, land not in production, land topology and landmark.
- **Latitude** and **Longitude** – the dashboards only map farms that have both. Records synced from KoboToolbox arrive with these filled in.
- **Farm Practices** tab – certification year and registration number, soil and water conservation, production and training programme.
- **Media** tab – the farm photo and audio, plus the **Polygon** field, which draws the plot outline from the boundary data.
- **Organization** and **Additional** tabs – FPO, Samithi ID and the other programme fields.

#### 2.6 Seasons and trainings

- **Farmer Season** – a season code and year, used to group purchases and trainings.
- **Farmer Training**, **Farmer Training Method**, **Farmer Training Status** and **Farmer Training Topic** – the vocabulary used on training records, each with a name and code.
- **Topic Category** – named `TP-<year>-<number>`, with a code, name and branch.
- **Training Status** – one training event per farmer. Training date and farmer are required; add the trainer, assistant, village, warehouse, season and photos on the attached table.

#### 2.7 Field staff (agents)

**Agent Type** is your list of officer types. **Agent** is one row per officer, holding their code, login ID and the current and allocated number sequences, plus the receipt number used for farmer cards and dealer receipts.

### 3. Record a purchase from a farmer

Purchases are **Farm Purchase Intake** documents. Open one from the **Farm Trace** or **KoboToolbox** workspace shortcut, or create it by hand when a delivery arrives without a form behind it.

Required fields are **Farmer**, **Crop**, **Purchase Date**, **UOM** and at least one row in **Collected Produce**. On the form:

- pick the **farmer** first – farmer group, gender, state and district are read-only and come from the farmer,
- **Season** is set from the year of the purchase date,
- in each Collected Produce row enter the **quantity**, the **unit price** and, if you use them, the **barcode**; the amount is calculated as quantity × unit price,
- **Total Qty** and **Total Amount** add themselves up,
- choose the **payment method** – Cash, Mobile Money or Bank – and fill in the matching section (mobile provider and number, or bank details).

Save and **Submit**. Only submitted purchases are counted on the dashboards.

### 4. Turn purchases into a Purchase Receipt

When the goods reach the store, convert the intake:

1. Open the submitted **Farm Purchase Intake** and use **Create > Purchase Receipt**. A draft Purchase Receipt is created for you with the farmer's supplier record, the posting date and one line per collected produce row.
2. Or start from the draft **Purchase Receipt** and use **Get Items From > Farm Purchase Intake** to select several intakes at once – filter by farmer and by a purchase date range. Intakes that already have a receipt are not offered.
3. All the intakes you select together must belong to the same farmer.
4. Every receipt line keeps a link back to its **Farm Purchase Intake** and to the **Transaction Barcode** of that line.
5. Submit the receipt: the intakes are flagged as receipted and stay picked up by the Purchase Dashboard. Cancelling or deleting the receipt releases them again so they can go into a new receipt.

### 5. Barcodes

Barcodes tag produce transactions. To create a batch:

1. Open **Kobo Toolbox Settings** (shortcut **Kobo Settings** in the **KoboToolbox** workspace) and press **Generate Barcodes**.
2. Enter how many codes you need. Each one is created as a **Barcode** record with an EAN-13 code and a printable image you can send to the printer.
3. Tick **Is Cancelled** on a code that is damaged or lost, so it is not handed out again.

Type or scan the code into the **barcode** field of a Collected Produce row. It travels with that line into the Purchase Receipt as **Transaction Barcode**.

### 6. Pull data in from KoboToolbox

Farm Trace reads submissions from the KoboToolbox **API** and writes them into the DocType you choose – usually **Farmer**, **Farm** or **Farm Purchase Intake**. Sync only runs when you press a sync button, so you can set everything up first and go live when you are ready.

#### 6.1 Collect your KoboToolbox details

1. **API URL** – `https://kf.kobotoolbox.org` for the global KoboToolbox, `https://eu.kobotoolbox.org` for the EU server, or the address of your own server.
2. **API token** – in KoboToolbox open **Account Settings > Security** and copy the API token.
3. **Asset UID** of each form – open the form in KoboToolbox and copy the long identifier from the form URL (`/a/<asset UID>`), or find it under **Settings > Form**.

#### 6.2 Save the connection

Open **Kobo Toolbox Settings** and fill in:

| Field | What to enter |
| --- | --- |
| API URL | your KoboToolbox server, for example `https://kf.kobotoolbox.org` |
| API Token | the token you copied |
| Enable Sync | tick when you are ready to bring data in |
| Sync Interval (minutes) | recorded on the form; the current release syncs when you press a sync button, not on a timer |

Press **Save**, then **Sync All Forms** to sync every enabled form in one go. That button only appears while **Enable Sync** is ticked.

#### 6.3 Map a Kobo form to Farm Trace

Create one **Kobo Form Configuration** per form (shortcut **Kobo Configuration**):

| Field | What to enter |
| --- | --- |
| Kobo Form Asset UID | the form's asset UID |
| Form Name | the name that shows up in the sync log |
| Enabled | tick to include this form in Sync All Forms |
| Target DocType | the DocType the submissions are written to, for example Farmer, Farm or Farm Purchase Intake |
| Match Field | the field that identifies an existing record, so that syncing again updates it instead of creating a duplicate |
| Field Mappings | one row per answered question you want to store |

In each **Field Mappings** row:

- **Kobo Field Name** – the question name from the form. The short name is enough: `first_name` also matches a question called `farmer_registration/first_name`.
- **Target Field** – the fieldname on the target DocType.
- **Kobo Repeat Group** and **Target Child Table** – for repeating questions only. Give the repeat group's name and the child table its rows belong in (for example the Collected Produce table on a Farm Purchase Intake). Leave both empty for header fields.

Useful **Match Field** choices: `farmer_id` when writing Farmers, `farm_id` for Farms, and `kobo_submission_id` for Farm Purchase Intake, so that every submission becomes its own purchase.

#### 6.4 Run a sync

- **Sync All Forms** on Kobo Toolbox Settings – every form configuration that is enabled.
- **Sync Now** on a Kobo Form Configuration – that one form. It needs the API token saved and the configuration ticked **Enabled**.
- The screen locks with a spinner while the sync runs, then a message such as `12 created, 3 updated, 1 skipped, 0 failed` tells you what happened.

#### 6.5 Read the sync log

Every run writes a **Kobo Sync Log** row (shortcut **Kobo Sync Log**), so a failed sync never fails silently.

| Column | Meaning |
| --- | --- |
| Sync Type | the form name from the configuration |
| Status | Success, Partial or Failed, depending on how many submissions failed |
| Triggered By | Manual or Scheduled |
| Started At / Ended At | when the run happened |
| Records Created / Updated / Failed | the counts behind the message you saw |
| Error Details | one line per failing submission (the first 20) |
| Response | the raw first page returned by the KoboToolbox API, kept for troubleshooting |

### 7. What a sync does to your records

#### Matching and updating

- An existing record is found through the **Match Field**; letter case is ignored when comparing.
- Records that are still in **draft** are updated in place, and their child rows are replaced with what KoboToolbox now holds.
- **Submitted or cancelled** documents are never overwritten. Only the linked farmer and the cached group, gender, state and district on the purchase are refreshed, and the submission is counted as **skipped** – so a purchase you have already receipted keeps its numbers.

#### Values that are cleaned up on the way in

- Text answers are stored in title case.
- GPS and boundary answers (`farm_gps`, `farm_boundary`, `gps`, `boundary`, `landmark`) are stored **exactly** as they arrive, because the map and the plot outline need the raw coordinates.
- Select answers are matched to the DocType's options: exact match first, then ignoring case, then by turning the Kobo slug into a label (`mobile` becomes `Mobile`). Payment methods are mapped as `cash` to Cash, `mobile` to Mobile Money and `bank` to Bank.
- A purchase arriving from Kobo is completed for you: a line takes its item from the crop when the form does not name one, amount becomes quantity × unit price, and the totals and the season are set from the rows and the purchase date.

#### Geography that is created for you

Submissions carry the answers **country**, **region**, **district** and **group**. Farm Trace looks each one up and creates what is missing, so new areas do not need setting up by hand:

- **State** comes from the region answer and **District** from the district answer.
- **Ward** and **Village** both come from the **group** answer, because the forms do not ask for a village.
- **Farmer Group** is named exactly as the group answer, which normally already contains the district.
- On the linked **Farmer**, village, group, district, state and country are filled in **only when they are empty** – details your team already entered are never overwritten.

#### Farmers that are created for you

When a Farm or Farm Purchase Intake submission names a farmer who does not exist yet, Farm Trace creates a stub **Farmer** so the submission is not lost: the Kobo value becomes the farmer ID and code, the name and phone answers fill in the personal details, and the record is named `Farmer <value>` until somebody completes it. The value is first matched against existing farmer IDs, farmer codes, phone numbers and mobile numbers, so a farmer you already know is linked rather than duplicated.

#### Photos and farm maps

- **Farmer > Contract Image** and **Farm > Photo** are filled from the form's image questions (anything matching `photo_farmer`, `farmer_photo` or `photo` for a farmer, and `photo_farm`, `farm_photo` or `photo` for a farm). The photo is downloaded, turned upright if the phone stored its rotation in the EXIF data, and attached as a public file. Other images are not downloaded.
- On a **Farm**, the GPS answer fills latitude and longitude, and the boundary answer fills the landmark. Those are what draw the plot outline on the form and place the farm on the dashboard maps.

### 8. Workspaces and dashboards

| Workspace | What is on it |
| --- | --- |
| **Farm Trace** | shortcuts to Farm, Farmer, Farmer Group and Farm Purchases; cards for the master DocTypes (Farm, Farmer, Farmer Group), the trainings group (Farmer Training, Farmer Training Method, Farmer Training Status, Farmer Training Topic, Topic Category) and the geography group (Farmer Group, Village, Ward, District, State, Country) |
| **FarmTrace Dashboard** | number cards for Farm, Farmer, Farmer Groups, Village, Ward, District and States, plus the Farms Map and satellite map of every farm that has coordinates |
| **Purchase Dashboard** | number cards Farmers, Farms, Hectares, Kg bought, Kg dispatched, Open markets; charts Kg bought per week, Procurement by Region, Procurement by Farmer Group, Procurement by Payment Method, Payment by Mobile Service Provider, Kg bought by district, Purchase Summary by Gender; panels Compliance by standard, Field activity, Premium to farmers, Contracts, Markets still open, Groups, Latest purchases, Officer activity |
| **KoboToolbox** | shortcuts to Kobo Settings, Kobo Configuration, Kobo Sync Log and Farm Purchase Intake |

What some of the numbers mean:

- **Kg bought** counts every submitted purchase; **Kg dispatched** counts only purchases that already have a Purchase Receipt behind them.
- **Hectares** adds up the farms whose hectares were entered as a number, and **Open markets** counts farmer groups that still have a purchase waiting for a receipt.
- **Latest purchases** lists the newest intakes as Open or Closed (closed means receipted), and **Markets still open**, **Groups** and **Officer activity** break the same purchases down by market centre, farmer group and the KoboToolbox user who submitted them.
- **Compliance by standard** counts farms per certification, **Field activity** shows the last 90 days of activity, and **Premium to farmers** and **Contracts** show an empty state until your site has premium and contract data for them to read.

### 9. Troubleshooting

| What you see | What it means | What to do |
| --- | --- | --- |
| "Kobo sync is disabled. Enable it in Kobo Toolbox Settings." | Sync All Forms was pressed while Enable Sync was off | tick **Enable Sync**, save, and press the button again |
| "API Token is required in Kobo Toolbox Settings." | no token is stored | paste the token you copied from KoboToolbox and save |
| "This form configuration is disabled." | Sync Now was pressed on a form that is not enabled | tick **Enabled** on the form configuration |
| "No field mappings configured" | the form has no Field Mappings rows | add the questions you want to store and sync again |
| "Submission missing match field ..." in the sync log | a submission left the Match Field question blank, or the mapping is missing | map the question, then sync again – the records that worked are updated, not duplicated |
| "Kobo API error: ..." | wrong API URL or token, or the Asset UID is not reachable with that token | check the three values in section 6.1 |
| Every submission is counted as skipped | the records already exist in submitted or cancelled state | expected – submitted documents are never overwritten |
| A farmer shows up as "Farmer <value>" | the Kobo answer matched no existing farmer ID, code, phone or mobile number | open the Farmer and complete the details |
| The farm polygon says "No boundary data yet" | the form had no boundary answer, or the coordinates did not parse | sync again once the field team captures the boundary |
| Charts are empty for older purchases | those records predate the reporting fields | run `bench --site <your-site> migrate` – the app's patch backfills farmer group, gender, state and district on existing purchases |
| Barcode generation fails | the `python-barcode` library is missing from the environment | install it in the bench environment (section 1) and try again |

### 10. Who can do what

- Every Farm Trace DocType currently grants the standard rights to **System Manager**: read, write, create and delete, plus submit and cancel where the DocType is submittable.
- **Farm Purchase Intake** is submittable, so purchases are submitted and cancelled rather than deleted quietly. **Barcode**, **Kobo Sync Log** and the master DocTypes are ordinary records.
- Kobo syncs write with elevated rights, so whoever presses the sync button does not need write access to the target DocType – but they do need access to the Kobo settings and form configurations, which means System Manager.
- For day-to-day data entry, create a role for your team and grant it the rights it needs in **Role Permission Manager** instead of handing out System Manager.

### For developers

- Install from a checkout with `bench get-app <repo> --branch develop`, then `bench --site <site> install-app farmtrace`.
- Formatting and linting use `pre-commit`: run `pre-commit install` once, then `pre-commit run --all-files` (ruff, eslint, prettier, pyupgrade).
- CI installs the app and runs the unit tests on every push to `develop`, and runs Frappe Semgrep rules plus pip-audit on pull requests.
- The test suite, the linting setup and the test-record pruning rules are documented in [TESTING.md](TESTING.md).

### License

agpl-3.0
