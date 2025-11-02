---
hide:
  - toc
  - navigation
---


# SPRINT

<div class="hero-section">
    <img src="tests/aug-22-hotfire/firing.gif" alt="SPRINT Hot Fire Test" class="hero-gif">
    <div class="hero-text">
        <p>SPRINT is a project that officially began just one month prior to its first hotfire at Launch Canada.</p>
        <p>SPRINT's modular architecture supports quick configuration changes, efficient testing, and fast learning. The results of our hotfire puts us on track to flying our flight-weight system now in development.</p>
    </div>
</div>


## Tests

<div class="test-gallery">

    <div class="test-item">
        <img src="tests/sept-13-hotfire/thmbnl.png" alt="September Hot-fire Test">
        <h3>Hot Fire Test - September 13th & 14th, 2025</h3>
        <p>Multi-day hot-fire test campaign demonstrating improved engine performance and system reliability across multiple firing sequences.</p>
        <a href="tests/sept-13-hotfire/" class="find-out-more">Find out more →</a>
    </div>

    <div class="test-item">
        <img src="tests/aug-22-hotfire/thmbnl.png" alt="Hot-fire Test">
        <h3>Hot Fire Test - August 22nd, 2025</h3>
        <p>Hot-fire test of the SPRINT system demonstrating successful ignition and combustion.</p>
        <a href="tests/aug-22-hotfire/" class="find-out-more">Find out more →</a>
    </div>

    <div class="test-item">
        <img src="tests/aug-19-coldflow/thmbnl.png" alt="Cold-flow Test">
        <h3>Cold Flow Test - August 9th, 2025</h3>
        <p>Cold-flow test validating fluid dynamics and system integration.</p>
        <a href="tests/aug-19-coldflow/" class="find-out-more">Find out more →</a>
    </div>

</div>

<style>
    .hero-section {
        display: flex;
        align-items: center;
        gap: 2rem;
        margin: 2rem 0 3rem 0;
        flex-wrap: wrap;
    }
    
    .hero-gif {
        flex: 1;
        min-width: 300px;
        max-width: 500px;
        width: auto;
        height: auto;
        object-fit: contain;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .hero-text {
        flex: 1;
        min-width: 300px;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    
    @media (max-width: 768px) {
        .hero-section {
            flex-direction: column;
        }
        
        .hero-gif {
            max-width: 100%;
        }
    }
    
    .system-overview {
        margin: 3rem 0;
        text-align: center;
    }
    
    .overview-image {
        width: 100%;
        max-width: 800px;
        height: auto;
        object-fit: cover;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .overview-caption {
        margin-top: 1rem;
        font-style: italic;
        color: #666;
        font-size: 0.9rem;
    }
    
    .subsystem-gallery, .test-gallery {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 2rem;
        margin: 2rem 0;
    }

    .subsystem-item, .test-item {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .subsystem-item:hover, .test-item:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }

    .subsystem-item img, .test-item img {
        width: 100%;
        height: 200px;
        object-fit: cover;
        border-radius: 5px;
    }

    .leads-section {
        margin: 2rem 0;
    }

    .leads-item {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        display: flex;
        gap: 2rem;
        align-items: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .leads-item:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }

    .leads-item img {
        width: 300px;
        height: 200px;
        object-fit: cover;
        border-radius: 5px;
        flex-shrink: 0;
    }

    .leads-content {
        flex: 1;
    }

    .leads-content p {
        font-size: 1.1rem;
        margin-bottom: 1rem;
    }

    @media (max-width: 768px) {
        .leads-item {
            flex-direction: column;
        }

        .leads-item img {
            width: 100%;
            max-width: 100%;
        }
    }
    
    .find-out-more {
        display: inline-block;
        margin-top: 1rem;
        padding: 0.5rem 1rem;
        background-color: #0066cc;
        color: white !important;
        text-decoration: none;
        border-radius: 4px;
        transition: background-color 0.3s ease;
    }
    
    .find-out-more:hover {
        background-color: #004c99;
        color: white !important;
    }
</style>



<!-- ## Links

- [BOM](https://docs.google.com/spreadsheets/d/14efr8l9_zVHHuwc9b49hxxgiD6_vnU3ExFUFa4B9Yjg/edit?usp=sharing)

- [CAD](https://github.com/marstmu/4in-liquid-rocket)

## Documents

- Mojave Sphinx book: [HCR-5100](HCR-5100%20-%20Mojave%20Sphinx%20Build,%20Integration,%20and%20Launch%20Guidebook%20-%20R01-2.pdf)

- [FAR-OUT Rules](FAR-OUT+Rules+and+Requirements+Document+rev+2024-10-02.pdf)

- Launch Canada 
    - [Design, Test & Evaluation Guide](Launch+Canada+Design,+Test+&+Evaluation+Guide+R3+(2).pdf)
    - [2025 Rules & Requirements Guide](Launch+Canada+Rules+and+Requirements+Guide+2025R3.pdf) -->