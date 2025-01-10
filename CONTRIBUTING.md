# Contributing

Thank you for considering contributing to this project!  
This guide will walk you through adding or updating a summer school listing in the repository.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Adding or Updating a Summer School](#adding-or-updating-a-summer-school)
3. [Attributes and Format](#attributes-and-format)
4. [Example Entry](#example-entry)
5. [Pull Requests](#pull-requests)

---

## Getting Started

1. **[Fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo)** this repository to your own GitHub account.
2. **[Clone](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo#cloning-your-forked-repository)** the forked repository onto your local machine.
3. **[Create a new branch](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-and-deleting-branches-within-your-repository)** for your changes (e.g., `my-summer-school-addition`).

---

## Adding or Updating a Summer School

1. Open the file `site/_data/summerschools.yml`.
2. Add or update an existing entry in the list, following the [Attributes and Format](#attributes-and-format) guidelines below.
3. Commit your changes and push them to your forked repository.
4. **[Open a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request)** (PR) against this repository.

---

## Attributes and Format

Please ensure that each summer school entry in `summerschools.yml` has the following **required** attributes.  
Optional attributes are also listed below—though not mandatory, they help provide more context and clarity for prospective attendees.

### **Required Attributes**

- **`title`**  
  Short name of the summer school.  
  Example: `Awesome ML Summer School`.

- **`year`**  
  The year in which the summer school takes place.  
  Example: `2025`.

- **`id`**  
  A unique identifier.  
  Typically the title (lowercase, no spaces) plus the last two digits of the year, e.g., `awesomemlschool25`.

- **`full_name`**  
  The full official name of the school if it differs from the short title.  
  Example: `1st International Summer School on Generic AI Topics`.

- **`link`**  
  The URL where people can find more information or apply.  
  Example: `https://awesomemlschool.org`.

- **`deadline`**  
  The application deadline in the format `YYYY-MM-DD HH:MM`.  
  Example: `2025-05-01 23:59`.

- **`timezone`**  
  The timezone for the deadline, e.g., `UTC`, `America/New_York`, `Europe/Berlin`.  
  Please use one of the timezones listed in [timezones.md](timezones.md).

- **`place`**  
  Where the summer school will be held.  
  Example: `City, Country`.

- **`date`**  
  A human-readable string of the date range.  
  Example: `June 1 - June 5, 2025`.

- **`start`**  
  The start date in `YYYY-MM-DD` format.  
  Example: `2025-06-01`.

- **`end`**  
  The end date in `YYYY-MM-DD` format.  
  Example: `2025-06-05`.

- **`sub`**  
  A list of topics that apply to this summer school (e.g., `ML`, `NLP`, `CV`).  
  See [topics.md](topics.md) for valid values.  
  Example: `['ML', 'NLP']`.

### **Optional Attributes**

- **`note`**  
  Any important notes about the school (e.g., registration info, special format changes).

- **`email`**  
  A contact email for questions regarding the school.  
  Example: `contact@awesomemlschool.org`.

- **`description`**  
  A longer-form description of the summer school.  
  You can include details such as the target audience, scope, and unique features.

- **`image`**  
  A link to an official image or logo for the summer school.  
  Example: `https://awesomemlschool.org/logo.png`.

- **`location`**  
  - **`latitude`** and **`longitude`** for the venue, useful for mapping or geolocation features.

- **`series`**  
  The name of the overall series, if this summer school is part of a multi-year recurring series.  
  Example: `International Summer School on Awesome ML Topics`.

---

## Example Entry

Below is a fully populated, generic example with both required and optional attributes:

```yaml
- title: "Awesome ML Summer School"
  year: 2025
  id: amlss25
  full_name: "1st International Summer School on Awesome ML Topics"
  link: "https://awesomemlschool.org/"
  deadline: "2025-05-01 23:59:00"
  timezone: "UTC"
  place: "City, Country"
  date: "June 1 - June 5, 2025"
  start: 2025-06-01
  end: 2025-06-05
  sub: ['ML', 'NLP']
  note: "Applications will be reviewed on a rolling basis."
  email: "contact@awesomemlschool.org"
  description: "This summer school covers a broad range of topics in AI,
                from fundamental machine learning concepts to advanced research
                areas. Attendees will participate in interactive workshops
                and networking events."
  image: "https://awesomemlschool.org/logo.png"
  location:
    latitude: 12.3456
    longitude: 65.4321
  series: "International Summer School on Awesome ML Topics"
```